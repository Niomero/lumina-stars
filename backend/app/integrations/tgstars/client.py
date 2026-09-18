from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

import httpx

from app.core.config import get_settings
from app.integrations.tgstars.exceptions import TgStarsAuthError, TgStarsError, TgStarsUnavailable

log = logging.getLogger("TGSTARS")

MIN_INTERVAL_SECONDS = 2.1


class TgStarsClient:
    """Real Client API wrapper. Endpoints taken from official swagger."""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        settings = get_settings()
        self.base_url = (api_url or settings.tgstars_api_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.tgstars_api_key
        self._last_call = 0.0

    def _headers(self, request_id: str) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Request-Id": request_id,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _throttle(self) -> None:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise TgStarsAuthError("TGSTARS_API_KEY не задан")
        self._throttle()
        request_id = str(uuid.uuid4())
        url = f"{self.base_url}{path}"
        log.info("request %s %s rid=%s", method, path, request_id)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.request(
                    method, url, params=params, json=json, headers=self._headers(request_id)
                )
        except httpx.TimeoutException as exc:
            raise TgStarsUnavailable("TGStars API timeout") from exc
        except httpx.HTTPError as exc:
            raise TgStarsUnavailable("TGStars API connection error") from exc

        if response.status_code in (401, 403):
            raise TgStarsAuthError("TGStars API auth failed", response.status_code)
        if response.status_code == 503:
            raise TgStarsUnavailable("TGStars API unavailable", 503)
        if response.status_code >= 400:
            payload = None
            try:
                payload = response.json()
            except Exception:
                payload = {"text": response.text[:500]}
            raise TgStarsError(f"TGStars API error {response.status_code}", response.status_code, payload)
        try:
            return response.json()
        except Exception as exc:
            raise TgStarsError("Invalid JSON from TGStars") from exc

    def get_balance(self) -> dict:
        return self.request("GET", "/balance")

    def get_stars_rate(self) -> dict:
        return self.request("GET", "/stars/rate")

    def check_username(self, username: str, type: str = "stars", months: int | None = None) -> dict:
        params: dict[str, Any] = {"username": username.lstrip("@"), "type": type}
        if months is not None:
            params["months"] = months
        return self.request("GET", "/username/check", params=params)

    def create_stars_order(self, username: str, quantity: int) -> dict:
        return self.request(
            "POST",
            "/orders/stars",
            json={"username": username.lstrip("@"), "quantity": quantity},
        )

    def create_premium_order(self, username: str, months: int) -> dict:
        return self.request(
            "POST",
            "/orders/premium",
            json={"username": username.lstrip("@"), "months": months},
        )

    def get_order(self, order_id: int) -> dict:
        return self.request("GET", f"/orders/{order_id}")

    def get_nft_rent_rate(self, nft_address: str, days: int | None = None) -> dict:
        params: dict[str, Any] = {"nft_address": nft_address}
        if days is not None:
            params["days"] = days
        return self.request("GET", "/rent/nft/rate", params=params)
