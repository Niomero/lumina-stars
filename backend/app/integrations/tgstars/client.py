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
                if response.status_code == 429:
                    wait = 2.2
                    try:
                        wait = float((response.json() or {}).get("retry_after") or 2.2)
                    except Exception:
                        pass
                    time.sleep(min(max(wait, 2.1), 6.0) + 0.15)
                    self._last_call = time.monotonic()
                    response = client.request(
                        method, url, params=params, json=json, headers=self._headers(str(uuid.uuid4()))
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

    def get_username_rent_rate(self, nft_address: str, days: int | None = None) -> dict:
        params: dict[str, Any] = {"nft_address": nft_address}
        if days is not None:
            params["days"] = days
        return self.request("GET", "/rent/username/rate", params=params)

    def get_number_rent_rate(self, nft_address: str, days: int | None = None) -> dict:
        params: dict[str, Any] = {"nft_address": nft_address}
        if days is not None:
            params["days"] = days
        return self.request("GET", "/rent/number/rate", params=params)

    def create_nft_rent(self, nft_address: str, days: int | None = None) -> dict:
        body: dict[str, Any] = {"nft_address": nft_address}
        if days is not None:
            body["days"] = days
        return self.request("POST", "/orders/rent/nft", json=body)

    def create_username_rent(self, nft_address: str, days: int | None = None) -> dict:
        body: dict[str, Any] = {"nft_address": nft_address}
        if days is not None:
            body["days"] = days
        return self.request("POST", "/orders/rent/username", json=body)

    def create_number_rent(self, nft_address: str, days: int | None = None) -> dict:
        body: dict[str, Any] = {"nft_address": nft_address}
        if days is not None:
            body["days"] = days
        return self.request("POST", "/orders/rent/number", json=body)

    def rent_connect(self, transaction_id: int, tonconnect_url: str) -> dict:
        return self.request(
            "POST",
            "/orders/rent/connect",
            json={"transaction_id": transaction_id, "tonconnect_url": tonconnect_url},
        )

    def nft_buy_collections(self) -> dict:
        return self.request("GET", "/nft/buy/collections")

    def nft_buy_list(self, **params) -> dict:
        clean = {k: v for k, v in params.items() if v not in (None, "")}
        return self.request("GET", "/nft/buy/list", params=clean or None)

    def nft_buy_info(self, nft_address: str) -> dict:
        return self.request("GET", "/nft/buy/info", params={"nft_address": nft_address})

    def buy_nft(self, nft_address: str) -> dict:
        return self.request("POST", "/orders/nft/buy", json={"nft_address": nft_address})

    def transfer_nft_telegram(self, transaction_id: int, username: str) -> dict:
        return self.request(
            "POST",
            "/orders/nft/transfer/telegram",
            json={"transaction_id": transaction_id, "username": username.lstrip("@")},
        )

    def transfer_nft_wallet(self, transaction_id: int, wallet_address: str) -> dict:
        return self.request(
            "POST",
            "/orders/nft/transfer/wallet",
            json={"transaction_id": transaction_id, "wallet_address": wallet_address},
        )

    def rent_nft_collections(self) -> dict:
        return self.request("GET", "/rent/nft/collections")

    def rent_nft_list(self, collection_address: str, **params) -> dict:
        query = {"collection_address": collection_address, **{k: v for k, v in params.items() if v not in (None, "")}}
        return self.request("GET", "/rent/nft/list", params=query)

    def rent_username_list(self, **params) -> dict:
        clean = {k: v for k, v in params.items() if v not in (None, "")}
        return self.request("GET", "/rent/username/list", params=clean or None)

    def rent_number_list(self, **params) -> dict:
        clean = {k: v for k, v in params.items() if v not in (None, "")}
        return self.request("GET", "/rent/number/list", params=clean or None)
