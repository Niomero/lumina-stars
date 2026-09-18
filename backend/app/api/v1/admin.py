from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require
from app.api.serializers import order_public, tx_public, user_public
from app.core.errors import AppError, NotFoundError
from app.core.money import money
from app.core.rbac import Role
from app.db.session import get_db
from app.models import (
    AuditLog,
    Balance,
    Mirror,
    MirrorTransaction,
    Order,
    Product,
    Transaction,
    User,
)
from app.services.audit import write_audit
from app.services.orders import _lock_balance, refund_order
from app.services.payments import get_payment_provider

router = APIRouter(prefix="/admin", tags=["admin"])


def _period_from(period: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    if period in {"24h", "today"}:
        return now - timedelta(hours=24)
    if period == "7d":
        return now - timedelta(days=7)
    if period == "30d":
        return now - timedelta(days=30)
    return None


def _scope_user_ids(actor: User, db: Session) -> list[int] | None:
    if actor.role in {Role.ADMIN.value, Role.SUPERADMIN.value, Role.MANAGER.value}:
        return None
    if actor.role == Role.MIRROR_OWNER.value:
        mirrors = list(db.scalars(select(Mirror.id).where(Mirror.owner_user_id == actor.id)))
        if not mirrors:
            return []
        ids = list(db.scalars(select(User.id).where(User.mirror_id.in_(mirrors))))
        return ids
    return []


@router.get("/overview")
def overview(period: str = "7d", actor: User = Depends(require("analytics.read")), db: Session = Depends(get_db)):
    since = _period_from(period)
    order_q = select(Order)
    user_q = select(func.count()).select_from(User)
    if since:
        order_q = order_q.where(Order.created_at >= since)
        user_q = user_q.where(User.created_at >= since)
    scoped = _scope_user_ids(actor, db)
    if scoped is not None:
        order_q = order_q.where(Order.user_id.in_(scoped or [-1]))
        user_q = select(func.count()).select_from(User).where(User.id.in_(scoped or [-1]))
    orders = list(db.scalars(order_q))
    paid = [o for o in orders if o.status in {"APPROVED", "COMPLETED", "PROCESSING"}]
    revenue = sum((o.total_price for o in paid), Decimal("0.00"))
    profit = sum((o.profit for o in paid), Decimal("0.00"))
    users = db.scalar(user_q) or 0
    mirrors = db.scalar(select(func.count()).select_from(Mirror)) or 0
    return {
        "success": True,
        "data": {
            "users": int(users),
            "orders": len(orders),
            "revenue": f"{revenue:.2f}",
            "profit": f"{profit:.2f}",
            "mirrors": int(mirrors),
            "avg_order": f"{(revenue / len(paid) if paid else Decimal('0')):.2f}",
        },
    }


@router.get("/users")
def users(
    q: str | None = None,
    page: int = 1,
    limit: int = 20,
    actor: User = Depends(require("users.read")),
    db: Session = Depends(get_db),
):
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    if q:
        like = f"%{q}%"
        filt = User.username.ilike(like) | User.first_name.ilike(like) | User.referral_code.ilike(like)
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.order_by(User.id.desc()).offset((page - 1) * limit).limit(limit)))
    out = []
    for u in items:
        bal = db.scalar(select(Balance.amount).where(Balance.user_id == u.id)) or 0
        out.append(user_public(u, balance=bal))
    return {"success": True, "data": {"items": out, "total": int(total), "page": page, "limit": limit}}


class PatchUserIn(BaseModel):
    is_blocked: bool | None = None
    role: str | None = None
    adjust_amount: Decimal | None = None
    adjust_reason: str | None = None


@router.get("/users/{user_id}")
def user_detail(user_id: int, actor: User = Depends(require("users.read")), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("Пользователь не найден")
    bal = db.scalar(select(Balance.amount).where(Balance.user_id == user.id)) or 0
    orders = list(db.scalars(select(Order).options(selectinload(Order.product)).where(Order.user_id == user.id).order_by(Order.id.desc()).limit(20)))
    txs = list(db.scalars(select(Transaction).where(Transaction.user_id == user.id).order_by(Transaction.id.desc()).limit(20)))
    return {
        "success": True,
        "data": {
            "user": user_public(user, balance=bal),
            "orders": [order_public(o) for o in orders],
            "transactions": [tx_public(t) for t in txs],
        },
    }


@router.patch("/users/{user_id}")
def patch_user(user_id: int, body: PatchUserIn, actor: User = Depends(require("users.write")), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("Пользователь не найден")
    if body.is_blocked is not None:
        user.is_blocked = body.is_blocked
        write_audit(db, "user.block" if body.is_blocked else "user.unblock", actor.id, "user", user.id)
    if body.role and actor.role == Role.SUPERADMIN.value:
        user.role = body.role
        write_audit(db, "user.role", actor.id, "user", user.id, {"role": body.role})
    if body.adjust_amount is not None:
        from app.core.rbac import require_permission

        require_permission(actor.role, "balance.adjust")
        amt = money(body.adjust_amount)
        bal = _lock_balance(db, user.id)
        before = money(bal.amount)
        after = money(before + amt)
        if after < 0:
            raise AppError("INVALID_AMOUNT", "Баланс не может быть отрицательным")
        bal.amount = after
        db.add(
            Transaction(
                user_id=user.id,
                type="ADMIN_ADJUSTMENT",
                amount=amt,
                balance_before=before,
                balance_after=after,
                description=body.adjust_reason or "Корректировка администратора",
            )
        )
        write_audit(db, "balance.adjust", actor.id, "user", user.id, {"amount": str(amt)})
    db.commit()
    bal = db.scalar(select(Balance.amount).where(Balance.user_id == user.id)) or 0
    return {"success": True, "data": user_public(user, balance=bal)}


@router.get("/orders")
def admin_orders(
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
    actor: User = Depends(require("orders.read")),
    db: Session = Depends(get_db),
):
    stmt = select(Order).options(selectinload(Order.product), selectinload(Order.user))
    count = select(func.count()).select_from(Order)
    if status:
        stmt = stmt.where(Order.status == status)
        count = count.where(Order.status == status)
    scoped = _scope_user_ids(actor, db)
    if scoped is not None:
        stmt = stmt.where(Order.user_id.in_(scoped or [-1]))
        count = count.where(Order.user_id.in_(scoped or [-1]))
    total = db.scalar(count) or 0
    items = list(db.scalars(stmt.order_by(Order.id.desc()).offset((page - 1) * limit).limit(limit)))
    return {"success": True, "data": {"items": [order_public(o) for o in items], "total": int(total), "page": page}}


@router.post("/orders/{order_id}/refund")
def admin_refund(order_id: int, actor: User = Depends(require("orders.write")), db: Session = Depends(get_db)):
    order = db.scalar(select(Order).options(selectinload(Order.product)).where(Order.id == order_id))
    if not order:
        raise NotFoundError("Заказ не найден")
    order = refund_order(db, order, actor)
    return {"success": True, "data": order_public(order)}


class ProductIn(BaseModel):
    name: str
    description: str = ""
    category: str = "stars"
    kind: str = "stars"
    min_quantity: int = 50
    max_quantity: int = 10000
    step: int = 50
    fallback_unit_price: Decimal = Decimal("0")
    enabled: bool = True
    popular: bool = False
    sort_order: int = 0
    slug: str | None = None
    icon: str = "sparkles"


@router.get("/products")
def admin_products(actor: User = Depends(require("products.read")), db: Session = Depends(get_db)):
    items = list(db.scalars(select(Product).order_by(Product.sort_order, Product.id)))
    return {"success": True, "data": {"items": [
        {
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "kind": p.kind,
            "min_quantity": p.min_quantity,
            "max_quantity": p.max_quantity,
            "enabled": p.enabled,
            "popular": p.popular,
            "fallback_unit_price": f"{p.fallback_unit_price:.2f}",
            "sort_order": p.sort_order,
        }
        for p in items
    ]}}


@router.post("/products")
def create_product(body: ProductIn, actor: User = Depends(require("products.write")), db: Session = Depends(get_db)):
    slug = body.slug or body.name.lower().replace(" ", "-")
    product = Product(
        slug=slug,
        name=body.name,
        description=body.description,
        category=body.category,
        kind=body.kind,
        icon=body.icon,
        min_quantity=body.min_quantity,
        max_quantity=body.max_quantity,
        step=body.step,
        fallback_unit_price=money(body.fallback_unit_price),
        enabled=body.enabled,
        popular=body.popular,
        sort_order=body.sort_order,
        provider="tgstars",
    )
    db.add(product)
    write_audit(db, "product.create", actor.id, "product", slug)
    db.commit()
    db.refresh(product)
    return {"success": True, "data": {"id": product.id}}


class ProductPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    fallback_unit_price: Decimal | None = None
    popular: bool | None = None


@router.patch("/products/{product_id}")
def patch_product(product_id: int, body: ProductPatch, actor: User = Depends(require("products.write")), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise NotFoundError("Товар не найден")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    write_audit(db, "product.update", actor.id, "product", product.id)
    db.commit()
    return {"success": True, "data": {"id": product.id, "enabled": product.enabled}}


@router.delete("/products/{product_id}")
def delete_product(product_id: int, actor: User = Depends(require("products.write")), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise NotFoundError("Товар не найден")
    product.enabled = False
    write_audit(db, "product.disable", actor.id, "product", product.id)
    db.commit()
    return {"success": True, "data": {"id": product.id}}


class MirrorIn(BaseModel):
    name: str
    slug: str
    description: str = ""
    owner_user_id: int | None = None
    primary_color: str = "#7eb6ff"
    secondary_color: str = "#c9a46a"
    accent_color: str = "#3ee0a0"
    markup_percent: Decimal = Decimal("0")
    markup_fixed: Decimal = Decimal("0")
    commission_percent: Decimal = Decimal("0")
    bot_username: str | None = None
    logo: str | None = None


@router.get("/mirrors")
def mirrors(actor: User = Depends(require("mirrors.read")), db: Session = Depends(get_db)):
    stmt = select(Mirror)
    if actor.role == Role.MIRROR_OWNER.value:
        stmt = stmt.where(Mirror.owner_user_id == actor.id)
    items = list(db.scalars(stmt.order_by(Mirror.id.desc())))
    out = []
    for m in items:
        orders = list(db.scalars(select(Order).where(Order.mirror_id == m.id)))
        paid = [o for o in orders if o.status in {"APPROVED", "COMPLETED", "PROCESSING"}]
        revenue = sum((o.total_price for o in paid), Decimal("0"))
        profit = sum((o.profit for o in paid), Decimal("0"))
        out.append(
            {
                "id": m.id,
                "name": m.name,
                "slug": m.slug,
                "status": m.status,
                "enabled": m.enabled,
                "owner_user_id": m.owner_user_id,
                "markup_percent": f"{m.markup_percent:.2f}",
                "primary_color": m.primary_color,
                "secondary_color": m.secondary_color,
                "accent_color": m.accent_color,
                "description": m.description,
                "bot_username": m.bot_username,
                "orders": len(orders),
                "revenue": f"{revenue:.2f}",
                "profit": f"{profit:.2f}",
            }
        )
    return {"success": True, "data": {"items": out}}


@router.post("/mirrors")
def create_mirror(body: MirrorIn, actor: User = Depends(require("mirrors.write")), db: Session = Depends(get_db)):
    exists = db.scalar(select(Mirror).where(Mirror.slug == body.slug))
    if exists:
        raise AppError("SLUG_TAKEN", "Такой slug уже занят")
    owner_id = body.owner_user_id or actor.id
    mirror = Mirror(
        name=body.name,
        slug=body.slug,
        description=body.description,
        owner_user_id=owner_id,
        primary_color=body.primary_color,
        secondary_color=body.secondary_color,
        accent_color=body.accent_color,
        markup_percent=money(body.markup_percent),
        markup_fixed=money(body.markup_fixed),
        commission_percent=money(body.commission_percent),
        bot_username=body.bot_username,
        logo=body.logo,
        status="active",
        enabled=True,
    )
    db.add(mirror)
    write_audit(db, "mirror.create", actor.id, "mirror", body.slug)
    db.commit()
    db.refresh(mirror)
    return {
        "success": True,
        "data": {
            "id": mirror.id,
            "slug": mirror.slug,
            "webapp_url": f"?mirror={mirror.slug}",
            "bot_username": mirror.bot_username,
            "status": mirror.status,
        },
    }


class MirrorPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    markup_percent: Decimal | None = None
    primary_color: str | None = None
    bot_username: str | None = None


@router.patch("/mirrors/{mirror_id}")
def patch_mirror(mirror_id: int, body: MirrorPatch, actor: User = Depends(require("mirrors.write")), db: Session = Depends(get_db)):
    mirror = db.get(Mirror, mirror_id)
    if not mirror:
        raise NotFoundError("Зеркало не найдено")
    if actor.role == Role.MIRROR_OWNER.value and mirror.owner_user_id != actor.id:
        raise NotFoundError("Зеркало не найдено")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(mirror, k, v)
    write_audit(db, "mirror.update", actor.id, "mirror", mirror.id)
    db.commit()
    return {"success": True, "data": {"id": mirror.id, "enabled": mirror.enabled}}


@router.get("/analytics")
def analytics(period: str = "7d", actor: User = Depends(require("analytics.read")), db: Session = Depends(get_db)):
    since = _period_from(period)
    stmt = select(Order)
    if since:
        stmt = stmt.where(Order.created_at >= since)
    orders = list(db.scalars(stmt.order_by(Order.created_at)))
    buckets: dict[str, dict] = {}
    for o in orders:
        day = o.created_at.date().isoformat() if o.created_at else "unknown"
        bucket = buckets.setdefault(day, {"orders": 0, "revenue": Decimal("0"), "profit": Decimal("0")})
        bucket["orders"] += 1
        if o.status in {"APPROVED", "COMPLETED", "PROCESSING"}:
            bucket["revenue"] += o.total_price
            bucket["profit"] += o.profit
    series = [
        {"day": k, "orders": v["orders"], "revenue": f"{v['revenue']:.2f}", "profit": f"{v['profit']:.2f}"}
        for k, v in buckets.items()
    ]
    return {"success": True, "data": {"series": series}}


@router.get("/audit")
def audit(page: int = 1, limit: int = 50, actor: User = Depends(require("audit.read")), db: Session = Depends(get_db)):
    items = list(db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).offset((page - 1) * limit).limit(limit)))
    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": a.id,
                    "action": a.action,
                    "entity": a.entity,
                    "entity_id": a.entity_id,
                    "actor_id": a.actor_id,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in items
            ]
        },
    }


class SettingsIn(BaseModel):
    demo_mode: bool | None = None


@router.get("/settings")
def settings_get(actor: User = Depends(require("settings.write")), db: Session = Depends(get_db)):
    from app.core.config import get_settings

    s = get_settings()
    return {
        "success": True,
        "data": {
            "demo_mode": s.demo_mode,
            "referral_enabled": s.referral_enabled,
            "referral_percent": s.referral_percent,
            "mirrors_enabled": s.mirrors_enabled,
            "tgstars_enabled": s.tgstars_enabled,
            "payments_enabled": s.payments_enabled,
        },
    }
