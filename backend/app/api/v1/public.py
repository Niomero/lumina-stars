from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/boot")
def boot():
    settings = get_settings()
    username = (settings.telegram_bot_username or "").lstrip("@") or None
    return {
        "success": True,
        "data": {
            "app_name": settings.app_name,
            "demo_login_enabled": settings.demo_login_enabled,
            "bot_username": username,
            "app_env": settings.app_env,
        },
    }
