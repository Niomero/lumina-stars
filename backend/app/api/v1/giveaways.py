from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import DigitalOrder, Giveaway, GiveawayWinner, User
from app.services.giveaways import giveaway_public, join, tick

router = APIRouter(prefix="/giveaways", tags=["giveaways"])


@router.get("")
def list_giveaways(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tick(db)
    items = list(db.scalars(select(Giveaway).options(selectinload(Giveaway.product)).order_by(Giveaway.id.desc())))
    return {"success": True, "data": {"items": [giveaway_public(db, g, user_id=user.id) for g in items if g.status != "cancelled"]}}


@router.get("/{giveaway_id}")
def detail(giveaway_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tick(db)
    g = db.get(Giveaway, giveaway_id)
    if not g or g.status == "cancelled":
        raise NotFoundError("Розыгрыш не найден")
    data = giveaway_public(db, g, user_id=user.id)
    if g.status == "finished":
        winners = list(db.scalars(select(GiveawayWinner).where(GiveawayWinner.giveaway_id == g.id)))
        mine = next((w for w in winners if w.user_id == user.id), None)
        data["won"] = bool(mine)
        data["reward_status"] = mine.reward_status if mine else None
        data["winners_count"] = len(winners)
        if mine and mine.digital_order_id:
            order = db.get(DigitalOrder, mine.digital_order_id)
            if order:
                data["prize_order"] = order.public_id
                data["prize_code"] = (order.result or {}).get("code")
    return {"success": True, "data": data}


@router.post("/{giveaway_id}/join")
def join_giveaway(giveaway_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    g = db.get(Giveaway, giveaway_id)
    if not g:
        raise NotFoundError("Розыгрыш не найден")
    join(db, g, user)
    db.refresh(g)
    return {"success": True, "data": giveaway_public(db, g, user_id=user.id)}
