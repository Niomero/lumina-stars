from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.serializers import user_public
from app.db.session import get_db
from app.models import Balance, Order, User

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bal = db.scalar(select(Balance.amount).where(Balance.user_id == user.id)) or 0
    orders_count = db.scalar(select(func.count()).select_from(Order).where(Order.user_id == user.id)) or 0
    spent = db.scalar(
        select(func.coalesce(func.sum(Order.total_price), 0)).where(
            Order.user_id == user.id, Order.status.in_(["APPROVED", "COMPLETED", "PROCESSING"])
        )
    ) or 0
    return {
        "success": True,
        "data": user_public(
            user,
            balance=bal,
            extra={"orders_count": int(orders_count), "spent": f"{spent:.2f}"},
        ),
    }
