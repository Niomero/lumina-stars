from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import User

log = logging.getLogger("NOTIFY")


def send_telegram(user: User | None, text: str) -> None:
    if not user or not user.telegram_id or not text:
        return
    token = get_settings().telegram_bot_token
    if not token:
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": user.telegram_id, "text": text},
            timeout=15,
        )
    except Exception:
        log.warning("telegram notify failed user=%s", user.id)


def notify_owner(db: Session, text: str) -> None:
    from sqlalchemy import select

    settings = get_settings()
    user = db.scalar(select(User).where(User.telegram_id == settings.owner_telegram_id))
    send_telegram(user, text)
