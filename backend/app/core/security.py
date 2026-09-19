from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import parse_qsl

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import AuthError


def create_access_token(user_id: int, extra: Optional[dict] = None) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_ttl_hours),
        "iat": datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise AuthError("Сессия недействительна") from exc


def create_admin_token(user_id: int) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "typ": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.admin_unlock_hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_admin_token(token: str) -> dict:
    from app.core.errors import AdminLocked

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise AdminLocked("Сессия администратора истекла") from exc
    if payload.get("typ") != "admin":
        raise AdminLocked("Введите пароль администратора")
    return payload


def validate_telegram_init_data(init_data: str, max_age_seconds: int = 86400) -> dict:
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        raise AuthError("Telegram-бот не настроен")
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise AuthError("Некорректные данные Telegram")
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise AuthError("Подпись Telegram не прошла проверку")
    auth_date = int(parsed.get("auth_date") or 0)
    if auth_date and time.time() - auth_date > max_age_seconds:
        raise AuthError("Данные Telegram устарели, откройте приложение заново")
    user_raw = parsed.get("user")
    if not user_raw:
        raise AuthError("В данных Telegram нет пользователя")
    user = json.loads(user_raw)
    start_param = parsed.get("start_param") or parsed.get("startapp")
    return {"user": user, "start_param": start_param, "auth_date": auth_date}
