from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import DigitalOrder, DigitalProduct, User
from app.services.digital import CATEGORIES, GROUPS, list_products, order_public, product_public, purchase
from app.services.giveaways import tick

router = APIRouter(prefix="/digital", tags=["digital"])


class BuyIn(BaseModel):
    product_id: int
    extra: dict | None = None
    idempotency_key: str = Field(min_length=8, max_length=80)


@router.get("/catalog")
def catalog(
    group: str | None = None,
    category: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tick(db)
    items = [product_public(db, p) for p in list_products(db, group=group, category=category)]
    cats = sorted({p["category"] for p in items})
    return {
        "success": True,
        "data": {
            "items": items,
            "categories": [{"id": c, "label": CATEGORIES.get(c, c)} for c in cats],
            "groups": GROUPS,
        },
    }


@router.get("/products/{product_id}")
def detail(product_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(DigitalProduct, product_id)
    if not product or not product.enabled:
        raise NotFoundError("Товар не найден")
    return {"success": True, "data": product_public(db, product)}


@router.post("/orders")
def buy(body: BuyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = purchase(db, user=user, product_id=body.product_id, extra=body.extra, idempotency_key=body.idempotency_key)
    db.refresh(order)
    if not order.product:
        order = db.scalar(select(DigitalOrder).options(selectinload(DigitalOrder.product)).where(DigitalOrder.id == order.id))
    return {"success": True, "data": order_public(order, reveal=True)}


@router.get("/orders")
def my_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(DigitalOrder)
        .options(selectinload(DigitalOrder.product))
        .where(DigitalOrder.user_id == user.id)
        .order_by(DigitalOrder.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = list(db.scalars(stmt))
    return {"success": True, "data": {"items": [order_public(o, reveal=False) for o in items]}}


@router.get("/orders/{public_id}")
def order_detail(public_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.scalar(
        select(DigitalOrder).options(selectinload(DigitalOrder.product)).where(DigitalOrder.public_id == public_id)
    )
    if not order or order.user_id != user.id:
        raise NotFoundError("Заказ не найден")
    return {"success": True, "data": order_public(order, reveal=True)}
