from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Payment, User
from app.services.trust_pay import create_payment, get_owned, mark_user_paid, payment_public

router = APIRouter(prefix="/trust-pay", tags=["trust-pay"])


class CreateIn(BaseModel):
    amount: Decimal = Field(gt=0)


@router.post("/payments")
def api_create(body: CreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pay = create_payment(db, user, body.amount)
    return {"success": True, "data": payment_public(pay, include_card=True)}


@router.get("/payments")
def api_list(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Payment).where(Payment.user_id == user.id, Payment.provider == "trust_pay").order_by(Payment.id.desc())
    items = list(db.scalars(stmt.offset((page - 1) * limit).limit(limit)))
    return {"success": True, "data": {"items": [payment_public(p) for p in items], "page": page, "limit": limit}}


@router.get("/payments/{public_id}")
def api_get(public_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pay = get_owned(db, public_id, user)
    db.commit()
    staff = user.role in {"ADMIN", "SUPERADMIN", "MANAGER"}
    return {"success": True, "data": payment_public(pay, include_card=pay.user_id == user.id or staff)}


@router.post("/payments/{public_id}/paid")
def api_paid(public_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pay = get_owned(db, public_id, user)
    pay = mark_user_paid(db, pay, user)
    return {"success": True, "data": payment_public(pay, include_card=True)}


@router.get("/receipt/{public_id}")
def api_receipt(public_id: str, db: Session = Depends(get_db)):
    pay = db.scalar(select(Payment).where(Payment.public_id == public_id, Payment.provider == "trust_pay"))
    if not pay:
        raise NotFoundError("Платёж не найден")
    from app.services.trust_pay import _expire

    _expire(pay)
    db.commit()
    return {"success": True, "data": payment_public(pay, include_card=True)}
