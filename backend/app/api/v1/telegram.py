from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

import httpx
from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, AuthError
from app.db.session import SessionLocal
from app.models import BotIntent
from app.services.auth import provision_user
from app.services.trust_pay import create_payment, topup_reply

log = logging.getLogger("BOT")
router = APIRouter(prefix="/telegram", tags=["telegram"])


def _send(token: str, method: str, payload: dict):
    url = f"https://api.telegram.org/bot{token}/{method}"
    with httpx.Client(timeout=15) as client:
        return client.post(url, json=payload).json()


def _parse_amount(text: str) -> Decimal | None:
    raw = (text or "").strip().replace("₽", "").replace(" ", "").replace(",", ".")
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    if value <= 0:
        return None
    return value


def handle_bot_update(db: Session, body: dict) -> None:
    settings = get_settings()
    message = body.get("message") or body.get("edited_message") or {}
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    text = (message.get("text") or "").strip()
    chat_id = chat.get("id")
    tg_id = from_user.get("id") or chat_id
    if not chat_id or not text:
        return
    token = settings.telegram_bot_token
    webapp = (settings.telegram_webapp_url or "").rstrip("/")
    if webapp and "v=" not in webapp:
        webapp = f"{webapp}?v=c8bce14"

    def send(payload: dict):
        if not token:
            return
        payload.setdefault("chat_id", chat_id)
        _send(token, "sendMessage", payload)

    keyboard = {"keyboard": [[{"text": "Пополнить баланс"}]], "resize_keyboard": True}
    if webapp:
        keyboard["keyboard"].append([{"text": "Открыть магазин", "web_app": {"url": webapp}}])

    user = None
    if tg_id:
        user = provision_user(
            db,
            telegram_id=int(tg_id),
            username=from_user.get("username"),
            first_name=from_user.get("first_name"),
            last_name=from_user.get("last_name"),
            photo_url=None,
        )
        db.commit()

    lowered = text.lower()
    if text.startswith("/start"):
        send(
            {
                "text": "Lumina — бутик Telegram Stars.\nПополнение — перевод на карту или ЮMoney. Сначала укажите сумму.",
                "reply_markup": keyboard,
            }
        )
        return

    if text.startswith("/topup") or "пополнить" in lowered:
        if tg_id:
            intent = db.get(BotIntent, int(tg_id)) or BotIntent(telegram_id=int(tg_id))
            intent.intent = "topup_amount"
            db.merge(intent)
            db.commit()
        send({"text": "Введите сумму пополнения в ₽. Без суммы ссылка на оплату не выдаётся.", "reply_markup": keyboard})
        return

    intent_row = db.get(BotIntent, int(tg_id)) if tg_id else None
    if intent_row and intent_row.intent == "topup_amount":
        amount = _parse_amount(text)
        if amount is None:
            send({"text": "Введите сумму числом, например 500. Ссылка без суммы не создаётся."})
            return
        if not user:
            send({"text": "Не удалось определить пользователя Telegram"})
            return
        try:
            pay = create_payment(db, user, amount)
        except AppError as exc:
            send({"text": exc.message})
            return
        intent_row.intent = ""
        db.commit()
        text_out, markup = topup_reply(pay)
        send({"text": text_out, "reply_markup": markup})


@router.post("/webhook/{secret}")
async def webhook(secret: str, request: Request):
    settings = get_settings()
    if secret != settings.telegram_webhook_secret:
        raise AuthError("Bad webhook secret")
    body = await request.json()
    db = SessionLocal()
    try:
        handle_bot_update(db, body)
    except Exception:
        log.exception("webhook")
    finally:
        db.close()
    return {"ok": True}


@router.get("/bot")
def bot_info():
    settings = get_settings()
    if not settings.telegram_bot_token:
        return {"success": True, "data": {"configured": False}}
    data = _send(settings.telegram_bot_token, "getMe", {})
    return {"success": True, "data": {"configured": True, "bot": data.get("result")}}
