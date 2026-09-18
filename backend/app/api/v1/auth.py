from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.serializers import user_public
from app.db.session import get_db
from app.services.auth import login_demo, login_telegram

router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramIn(BaseModel):
    init_data: str
    mirror_slug: str | None = None


class DemoIn(BaseModel):
    name: str | None = None


@router.post("/telegram")
def auth_telegram(body: TelegramIn, db: Session = Depends(get_db)):
    user, token = login_telegram(db, body.init_data)
    return {"success": True, "data": {"token": token, "user": user_public(user)}}


@router.post("/demo")
def auth_demo(body: DemoIn | None = None, db: Session = Depends(get_db)):
    user, token = login_demo(db, (body.name if body else None) or "Lumina")
    return {"success": True, "data": {"token": token, "user": user_public(user), "demo": True}}
