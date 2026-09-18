from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Referral, ReferralReward, User

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.get("")
def referrals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = get_settings()
    invited = db.scalar(select(func.count()).select_from(Referral).where(Referral.owner_user_id == user.id)) or 0
    earned = db.scalar(
        select(func.coalesce(func.sum(ReferralReward.amount), 0)).where(
            ReferralReward.referral_id.in_(select(Referral.id).where(Referral.owner_user_id == user.id))
        )
    ) or 0
    webapp = settings.telegram_webapp_url or ""
    bot = "LStrarsbot"
    link = f"https://t.me/{bot}?start=ref_{user.referral_code}"
    if webapp:
        link = f"{webapp}?startapp=ref_{user.referral_code}"
    return {
        "success": True,
        "data": {
            "code": user.referral_code,
            "link": link,
            "percent": settings.referral_percent,
            "enabled": settings.referral_enabled,
            "invited": int(invited),
            "earned": f"{earned:.2f}",
        },
    }
