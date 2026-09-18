from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.serializers import tx_public
from app.db.session import get_db
from app.models import Balance, Transaction, User
from app.services.payments import get_payment_provider

router = APIRouter(tags=["balance"])


class DepositIn(BaseModel):
    amount: Decimal = Field(gt=0)


@router.get("/balance")
def get_balance(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bal = db.scalar(select(Balance.amount).where(Balance.user_id == user.id)) or Decimal("0")
    return {"success": True, "data": {"amount": f"{bal:.2f}", "currency": "RUB"}}


@router.post("/balance/deposit")
def deposit(body: DepositIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pay = get_payment_provider().deposit(db, user.id, body.amount, actor_id=user.id)
    bal = db.scalar(select(Balance.amount).where(Balance.user_id == user.id)) or Decimal("0")
    return {"success": True, "data": {"payment_id": pay.id, "amount": f"{bal:.2f}"}}


@router.get("/transactions")
def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = db.scalar(select(func.count()).select_from(Transaction).where(Transaction.user_id == user.id)) or 0
    items = list(
        db.scalars(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    )
    return {"success": True, "data": {"items": [tx_public(t) for t in items], "page": page, "limit": limit, "total": int(total)}}
