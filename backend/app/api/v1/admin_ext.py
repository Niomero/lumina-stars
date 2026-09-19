from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require
from app.core.errors import AppError, NotFoundError
from app.core.money import money
from app.db.session import get_db
from app.models import DigitalCode, DigitalOrder, DigitalProduct, Giveaway, GiveawayParticipant, GiveawayWinner, User
from app.services.audit import write_audit
from app.services.codes import mask_code, decrypt_code
from app.services.digital import CATEGORIES, add_codes, fulfill_manual, order_public, product_public, stock_of
from app.services.giveaways import cancel, finish, giveaway_public, tick, validate_payload

router = APIRouter(prefix="/admin", tags=["admin-ext"])


def _user_brief(u: User | None) -> dict | None:
    if not u:
        return None
    return {
        "id": u.id,
        "telegram_id": u.telegram_id,
        "username": u.username,
        "first_name": u.first_name,
    }


def _users_map(db: Session, ids: list[int]) -> dict[int, dict]:
    uniq = {i for i in ids if i}
    if not uniq:
        return {}
    rows = list(db.scalars(select(User).where(User.id.in_(uniq))))
    return {u.id: _user_brief(u) for u in rows}


class DigitalIn(BaseModel):
    slug: str | None = None
    name: str
    description: str = ""
    category: str
    group: str = "topup"
    provider: str = "inventory"
    region: str = ""
    currency: str = "RUB"
    face_value: str = ""
    price: Decimal = Decimal("0")
    delivery_type: str = "code"
    amount_mode: str = "fixed"
    markup_percent: Decimal = Decimal("0")
    min_amount: Decimal = Decimal("0")
    max_amount: Decimal = Decimal("0")
    extra_fields: list | None = None
    enabled: bool = True
    sort_order: int = 0


class DigitalPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    region: str | None = None
    enabled: bool | None = None
    extra_fields: list | None = None
    sort_order: int | None = None
    face_value: str | None = None
    amount_mode: str | None = None
    markup_percent: Decimal | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    delivery_type: str | None = None


class CodesIn(BaseModel):
    codes: str = Field(min_length=1)


class FulfillIn(BaseModel):
    code: str


class GiveawayIn(BaseModel):
    title: str
    description: str = ""
    image: str = ""
    reward_type: str = "balance"
    reward_product_id: int | None = None
    reward_amount: Decimal | None = None
    winner_count: int = 1
    finish_type: str = "time"
    finish_at: datetime | None = None
    max_participants: int | None = None


@router.get("/digital")
def admin_digital(actor: User = Depends(require("digital.read")), db: Session = Depends(get_db)):
    items = list(db.scalars(select(DigitalProduct).order_by(DigitalProduct.sort_order, DigitalProduct.id)))
    out = []
    for p in items:
        row = product_public(db, p)
        sold = int(
            db.scalar(select(func.count()).select_from(DigitalOrder).where(DigitalOrder.product_id == p.id, DigitalOrder.status == "completed"))
            or 0
        )
        row["sold"] = sold
        out.append(row)
    return {"success": True, "data": {"items": out, "categories": CATEGORIES}}


@router.post("/digital")
def create_digital(body: DigitalIn, actor: User = Depends(require("digital.write")), db: Session = Depends(get_db)):
    slug = (body.slug or body.name).lower().replace(" ", "-")[:80]
    if db.scalar(select(DigitalProduct.id).where(DigitalProduct.slug == slug)):
        raise AppError("SLUG_TAKEN", "Такой slug уже занят")
    if body.category not in CATEGORIES:
        raise AppError("INVALID_CATEGORY", "Неизвестная категория")
    p = DigitalProduct(
        slug=slug,
        name=body.name.strip(),
        description=body.description,
        category=body.category,
        group=body.group if body.group in {"topup", "games"} else "topup",
        provider="inventory",
        region=body.region[:16],
        currency=body.currency[:8],
        face_value=body.face_value[:32],
        price=money(body.price),
        delivery_type=body.delivery_type if body.delivery_type in {"code", "manual"} else "code",
        amount_mode=body.amount_mode if body.amount_mode in {"fixed", "custom"} else "fixed",
        markup_percent=money(body.markup_percent),
        min_amount=money(body.min_amount),
        max_amount=money(body.max_amount),
        extra_fields=body.extra_fields,
        enabled=body.enabled,
        sort_order=body.sort_order,
    )
    db.add(p)
    write_audit(db, "digital.create", actor.id, "digital_product", slug)
    db.commit()
    db.refresh(p)
    return {"success": True, "data": product_public(db, p)}


@router.patch("/digital/{product_id}")
def patch_digital(product_id: int, body: DigitalPatch, actor: User = Depends(require("digital.write")), db: Session = Depends(get_db)):
    p = db.get(DigitalProduct, product_id)
    if not p:
        raise NotFoundError("Товар не найден")
    data = body.model_dump(exclude_unset=True)
    for key in ("price", "markup_percent", "min_amount", "max_amount"):
        if key in data and data[key] is not None:
            data[key] = money(data[key])
    if data.get("amount_mode") and data["amount_mode"] not in {"fixed", "custom"}:
        data["amount_mode"] = "fixed"
    if data.get("delivery_type") and data["delivery_type"] not in {"code", "manual"}:
        data.pop("delivery_type")
    for k, v in data.items():
        setattr(p, k, v)
    write_audit(db, "digital.update", actor.id, "digital_product", p.id)
    db.commit()
    db.refresh(p)
    return {"success": True, "data": product_public(db, p)}


@router.post("/digital/{product_id}/codes")
def upload_codes(product_id: int, body: CodesIn, actor: User = Depends(require("digital.write")), db: Session = Depends(get_db)):
    p = db.get(DigitalProduct, product_id)
    if not p:
        raise NotFoundError("Товар не найден")
    lines = [ln.strip() for ln in body.codes.replace(",", "\n").splitlines()]
    return {"success": True, "data": add_codes(db, p, lines, actor.id)}


@router.get("/digital/{product_id}/codes")
def list_codes(product_id: int, actor: User = Depends(require("digital.read")), db: Session = Depends(get_db)):
    p = db.get(DigitalProduct, product_id)
    if not p:
        raise NotFoundError("Товар не найден")
    rows = list(db.scalars(select(DigitalCode).where(DigitalCode.product_id == product_id).order_by(DigitalCode.id.desc()).limit(200)))
    items = []
    for c in rows:
        plain = decrypt_code(c.code_enc)
        items.append(
            {
                "id": c.id,
                "status": c.status,
                "masked": mask_code(plain),
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "sold_at": c.sold_at.isoformat() if c.sold_at else None,
            }
        )
    return {"success": True, "data": {"items": items, "stock": stock_of(db, product_id)}}


@router.get("/digital-orders")
def admin_digital_orders(actor: User = Depends(require("digital.read")), db: Session = Depends(get_db)):
    items = list(db.scalars(select(DigitalOrder).options(selectinload(DigitalOrder.product)).order_by(DigitalOrder.id.desc()).limit(80)))
    users = _users_map(db, [o.user_id for o in items])
    out = []
    for o in items:
        row = order_public(o, reveal=False)
        row["user"] = users.get(o.user_id)
        row["user_id"] = o.user_id
        out.append(row)
    return {"success": True, "data": {"items": out}}


@router.post("/digital-orders/{public_id}/fulfill")
def admin_fulfill(public_id: str, body: FulfillIn, actor: User = Depends(require("digital.write")), db: Session = Depends(get_db)):
    order = db.scalar(select(DigitalOrder).options(selectinload(DigitalOrder.product)).where(DigitalOrder.public_id == public_id))
    if not order:
        raise NotFoundError("Заказ не найден")
    order = fulfill_manual(db, order, body.code, actor)
    return {"success": True, "data": order_public(order, reveal=False)}


@router.get("/giveaways")
def admin_giveaways(actor: User = Depends(require("giveaways.read")), db: Session = Depends(get_db)):
    tick(db)
    items = list(db.scalars(select(Giveaway).options(selectinload(Giveaway.product)).order_by(Giveaway.id.desc())))
    winner_rows = list(db.scalars(select(GiveawayWinner)))
    users = _users_map(db, [w.user_id for w in winner_rows])
    by_g: dict[int, list] = {}
    for w in winner_rows:
        by_g.setdefault(w.giveaway_id, []).append(
            {
                "user_id": w.user_id,
                "user": users.get(w.user_id),
                "reward_status": w.reward_status,
                "selected_at": w.selected_at.isoformat() if w.selected_at else None,
                "selection_method": w.selection_method,
                "digital_order_id": w.digital_order_id,
            }
        )
    out = []
    for g in items:
        row = giveaway_public(db, g)
        row["winners"] = by_g.get(g.id, [])
        out.append(row)
    return {"success": True, "data": {"items": out}}


@router.post("/giveaways")
def create_giveaway(body: GiveawayIn, actor: User = Depends(require("giveaways.write")), db: Session = Depends(get_db)):
    payload = body.model_dump()
    validate_payload(db, payload)
    g = Giveaway(
        title=body.title.strip(),
        description=body.description,
        image=body.image or "",
        reward_type=body.reward_type,
        reward_product_id=body.reward_product_id if body.reward_type == "product" else None,
        reward_amount=money(body.reward_amount or 0),
        winner_count=body.winner_count,
        finish_type=body.finish_type,
        finish_at=body.finish_at,
        max_participants=body.max_participants,
        status="active",
        created_by=actor.id,
    )
    db.add(g)
    write_audit(db, "giveaway.create", actor.id, "giveaway", body.title)
    db.commit()
    db.refresh(g)
    return {"success": True, "data": giveaway_public(db, g)}


@router.post("/giveaways/{giveaway_id}/finish")
def admin_finish(giveaway_id: int, actor: User = Depends(require("giveaways.write")), db: Session = Depends(get_db)):
    g = db.get(Giveaway, giveaway_id)
    if not g:
        raise NotFoundError("Розыгрыш не найден")
    g = finish(db, g, method="manual", actor_id=actor.id)
    return {"success": True, "data": giveaway_public(db, g)}


@router.post("/giveaways/{giveaway_id}/cancel")
def admin_cancel(giveaway_id: int, actor: User = Depends(require("giveaways.write")), db: Session = Depends(get_db)):
    g = db.get(Giveaway, giveaway_id)
    if not g:
        raise NotFoundError("Розыгрыш не найден")
    g = cancel(db, g, actor.id)
    return {"success": True, "data": giveaway_public(db, g)}


@router.get("/giveaways/{giveaway_id}/participants")
def admin_participants(giveaway_id: int, actor: User = Depends(require("giveaways.read")), db: Session = Depends(get_db)):
    items = list(db.scalars(select(GiveawayParticipant).where(GiveawayParticipant.giveaway_id == giveaway_id)))
    users = _users_map(db, [p.user_id for p in items])
    return {
        "success": True,
        "data": {
            "items": [
                {
                    "user_id": p.user_id,
                    "user": users.get(p.user_id),
                    "joined_at": p.joined_at.isoformat() if p.joined_at else None,
                }
                for p in items
            ]
        },
    }
