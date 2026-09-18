from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.tgstars.client import TgStarsClient
from app.models import Order


class OrderProcessor(ABC):
    @abstractmethod
    def process(self, db: Session, order: Order) -> Order:
        raise NotImplementedError


class DemoOrderProcessor(OrderProcessor):
    def process(self, db: Session, order: Order) -> Order:
        order.status = "APPROVED"
        payload = dict(order.payload or {})
        payload["processor"] = "demo"
        payload["message"] = "Заказ одобрен и передан"
        order.payload = payload
        return order


class RealOrderProcessor(OrderProcessor):
    def __init__(self, client: TgStarsClient | None = None):
        self.client = client or TgStarsClient()

    def process(self, db: Session, order: Order) -> Order:
        product = order.product
        recipient = (order.recipient or "").lstrip("@")
        if product.kind == "stars":
            result = self.client.create_stars_order(recipient, order.quantity)
        elif product.kind == "premium":
            result = self.client.create_premium_order(recipient, order.quantity)
        elif product.kind == "nft_rent":
            result = self.client.create_nft_rent(recipient, order.quantity)
        elif product.kind == "username_rent":
            result = self.client.create_username_rent(recipient, order.quantity)
        elif product.kind == "number_rent":
            result = self.client.create_number_rent(recipient, order.quantity)
        elif product.kind == "nft_buy":
            result = self.client.buy_nft(recipient)
        else:
            order.status = "FAILED"
            order.payload = {"error": "unsupported_product"}
            return order
        order.provider_order_id = str(result.get("transaction_id") or "")
        order.status = "PROCESSING"
        order.payload = {"provider": result}
        return order


def get_processor() -> OrderProcessor:
    settings = get_settings()
    if settings.demo_mode or not settings.tgstars_enabled:
        return DemoOrderProcessor()
    return RealOrderProcessor()
