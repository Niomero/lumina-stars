import json
import logging

import httpx
from fastapi import APIRouter, Header, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthError
from app.db.session import SessionLocal

log = logging.getLogger("BOT")
router = APIRouter(prefix="/telegram", tags=["telegram"])


def _send(token: str, method: str, payload: dict):
    url = f"https://api.telegram.org/bot{token}/{method}"
    with httpx.Client(timeout=15) as client:
        return client.post(url, json=payload).json()


@router.post("/webhook/{secret}")
async def webhook(secret: str, request: Request):
    settings = get_settings()
    if secret != settings.telegram_webhook_secret:
        raise AuthError("Bad webhook secret")
    body = await request.json()
    message = body.get("message") or body.get("edited_message") or {}
    chat = message.get("chat") or {}
    text = (message.get("text") or "").strip()
    chat_id = chat.get("id")
    if not chat_id:
        return {"ok": True}
    token = settings.telegram_bot_token
    webapp = settings.telegram_webapp_url
    if text.startswith("/start"):
        payload = text.split(maxsplit=1)[1] if " " in text else ""
        url = webapp
        if payload:
            url = f"{webapp}?startapp={payload}" if webapp else webapp
        keyboard = {
            "inline_keyboard": [[{"text": "Открыть Lumina", "web_app": {"url": url or "https://t.me/LStrarsbot"}}]]
        }
        if token:
            _send(
                token,
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": "Lumina — бутик Telegram Stars.\nНажмите кнопку, чтобы открыть магазин.",
                    "reply_markup": keyboard if webapp else None,
                },
            )
    return {"ok": True}


@router.get("/bot")
def bot_info():
    settings = get_settings()
    if not settings.telegram_bot_token:
        return {"success": True, "data": {"configured": False}}
    data = _send(settings.telegram_bot_token, "getMe", {})
    return {"success": True, "data": {"configured": True, "bot": data.get("result")}}
