from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.api.serializers import order_public
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Order, User
from app.services.orders import checkout

router = APIRouter(prefix="/orders", tags=["orders"])


class CreateOrderIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)
    recipient: str = ""
    nft_address: str | None = None
    idempotency_key: str = Field(min_length=8, max_length=80)


@router.post("")
def create_order(body: CreateOrderIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = checkout(
        db,
        user=user,
        product_id=body.product_id,
        quantity=body.quantity,
        recipient=body.recipient,
        idempotency_key=body.idempotency_key,
        nft_address=body.nft_address,
    )
    return {
        "success": True,
        "data": {
            **order_public(order),
            "headline": "Заказ одобрен и передан" if order.status == "APPROVED" else "Заказ создан",
        },
    }


@router.get("")
def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Order).options(selectinload(Order.product)).where(Order.user_id == user.id).order_by(Order.id.desc())
    total = db.scalar(select(func.count()).select_from(Order).where(Order.user_id == user.id)) or 0
    items = list(db.scalars(stmt.offset((page - 1) * limit).limit(limit)))
    return {"success": True, "data": {"items": [order_public(o) for o in items], "page": page, "limit": limit, "total": int(total)}}


@router.get("/{order_id}")
def get_order(order_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Order).options(selectinload(Order.product))
    if order_id.isdigit():
        stmt = stmt.where(Order.id == int(order_id), Order.user_id == user.id)
    else:
        stmt = stmt.where(Order.public_id == order_id.lstrip("#"), Order.user_id == user.id)
    order = db.scalar(stmt)
    if not order:
        raise NotFoundError("Заказ не найден")
    data = order_public(order)
    data["timeline"] = _timeline(order.status)
    return {"success": True, "data": data}


def _timeline(status: str) -> list[dict]:
    steps = ["PENDING", "PAID", "APPROVED", "DELIVERED"]
    mapping = {
        "PENDING": 0,
        "PROCESSING": 2,
        "APPROVED": 3,
        "COMPLETED": 3,
        "FAILED": 1,
        "CANCELLED": 0,
        "REFUNDED": 1,
    }
    current = mapping.get(status, 0)
    labels = {
        "PENDING": "Создан",
        "PAID": "Оплачен",
        "APPROVED": "Одобрен",
        "DELIVERED": "Передан",
    }
    out = []
    for i, key in enumerate(steps):
        out.append({"key": key, "label": labels[key], "done": i <= current and status not in {"FAILED", "CANCELLED"}})
    return out
