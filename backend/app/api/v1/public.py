from __future__ import annotations

import time

import httpx
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/public", tags=["public"])

_bot_cache: tuple[float, str | None] = (0.0, None)


def _bot_username() -> str | None:
    settings = get_settings()
    named = (settings.telegram_bot_username or "").lstrip("@")
    if named:
        return named
    global _bot_cache
    now = time.time()
    if now - _bot_cache[0] < 300:
        return _bot_cache[1]
    token = settings.telegram_bot_token
    username = None
    if token:
        try:
            data = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=8).json()
            username = (data.get("result") or {}).get("username")
        except Exception:
            username = _bot_cache[1]
    _bot_cache = (now, username)
    return username


@router.get("/boot")
def boot():
    settings = get_settings()
    return {
        "success": True,
        "data": {
            "app_name": settings.app_name,
            "demo_login_enabled": settings.demo_login_enabled,
            "bot_username": _bot_username(),
            "app_env": settings.app_env,
        },
    }
