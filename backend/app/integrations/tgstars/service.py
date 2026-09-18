from __future__ import annotations

import logging
import time
from typing import Any, Optional

from app.core.config import get_settings
from app.core.money import money
from app.integrations.tgstars.client import TgStarsClient
from app.integrations.tgstars.exceptions import TgStarsError

log = logging.getLogger("TGSTARS")

_rate_cache: dict[str, Any] = {"ts": 0.0, "data": None}


class TgStarsService:
    def __init__(self, client: Optional[TgStarsClient] = None):
        self.client = client or TgStarsClient()

    def get_stars_rate(self, use_cache: bool = True) -> dict:
        settings = get_settings()
        now = time.time()
        if use_cache and _rate_cache["data"] and now - _rate_cache["ts"] < 30:
            return _rate_cache["data"]
        # In DEMO keep the shop price the merchant set (1.32). Live rate is provider cost.
        if settings.demo_mode or not settings.tgstars_api_key:
            data = self._fallback_rate()
            _rate_cache.update(ts=now, data=data)
            return data
        try:
            raw = self.client.get_stars_rate()
            data = {
                "price_per_star": money(raw.get("price_per_star_rub") or settings.fallback_star_price_rub),
                "min_quantity": int(raw.get("min_quantity") or 50),
                "max_quantity": int(raw.get("max_quantity") or 10000),
                "stars_enabled": bool(raw.get("stars_enabled", True)),
                "source": "tgstars",
            }
        except TgStarsError as exc:
            log.warning("rate fallback: %s", exc)
            data = self._fallback_rate()
        _rate_cache.update(ts=now, data=data)
        return data

    def _fallback_rate(self) -> dict:
        settings = get_settings()
        return {
            "price_per_star": money(settings.fallback_star_price_rub),
            "min_quantity": 50,
            "max_quantity": 10000,
            "stars_enabled": True,
            "source": "fallback",
        }

    def quote_stars(self, quantity: int) -> dict:
        rate = self.get_stars_rate(use_cache=False)
        qty = max(rate["min_quantity"], min(quantity, rate["max_quantity"]))
        unit = money(rate["price_per_star"])
        return {
            "quantity": qty,
            "unit_price": unit,
            "total": money(unit * qty),
            "min_quantity": rate["min_quantity"],
            "max_quantity": rate["max_quantity"],
            "source": rate["source"],
        }

    def check_username(self, username: str, type: str = "stars", months: int | None = None) -> dict:
        settings = get_settings()
        if settings.demo_mode or not settings.tgstars_api_key:
            clean = username.lstrip("@").strip()
            valid = len(clean) >= 3 and clean.replace("_", "").isalnum()
            return {"valid": valid, "reason": None if valid else "not_found", "demo": True}
        try:
            return self.client.check_username(username, type=type, months=months)
        except TgStarsError as exc:
            log.warning("username check failed: %s", exc)
            return {"valid": True, "reason": None, "degraded": True}
