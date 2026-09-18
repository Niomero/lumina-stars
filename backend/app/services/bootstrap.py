from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, SystemSetting


PRODUCTS = [
    {
        "slug": "telegram-stars",
        "name": "Telegram Stars",
        "description": "Звёзды для подарков, реакций и цифровых товаров внутри Telegram.",
        "category": "stars",
        "icon": "sparkles",
        "kind": "stars",
        "provider_product_id": "stars",
        "min_quantity": 50,
        "max_quantity": 10000,
        "step": 50,
        "fallback_unit_price": Decimal("1.85"),
        "popular": True,
        "sort_order": 1,
    },
    {
        "slug": "premium-3",
        "name": "Telegram Premium · 3 месяца",
        "description": "Подписка Premium на 3 месяца. Больше лимитов, эксклюзивные стикеры и реакции.",
        "category": "premium",
        "icon": "crown",
        "kind": "premium",
        "provider_product_id": "premium-3",
        "min_quantity": 3,
        "max_quantity": 3,
        "step": 3,
        "fallback_unit_price": Decimal("266.33"),
        "popular": True,
        "sort_order": 2,
    },
    {
        "slug": "premium-6",
        "name": "Telegram Premium · 6 месяцев",
        "description": "Подписка Premium на полгода по более выгодной цене.",
        "category": "premium",
        "icon": "crown",
        "kind": "premium",
        "provider_product_id": "premium-6",
        "min_quantity": 6,
        "max_quantity": 6,
        "step": 6,
        "fallback_unit_price": Decimal("249.83"),
        "popular": True,
        "sort_order": 3,
    },
    {
        "slug": "premium-12",
        "name": "Telegram Premium · 12 месяцев",
        "description": "Год Telegram Premium. Максимальная выгода.",
        "category": "premium",
        "icon": "gem",
        "kind": "premium",
        "provider_product_id": "premium-12",
        "min_quantity": 12,
        "max_quantity": 12,
        "step": 12,
        "fallback_unit_price": Decimal("208.25"),
        "popular": False,
        "sort_order": 4,
    },
]


def seed(db: Session) -> None:
    for item in PRODUCTS:
        existing = db.scalar(select(Product).where(Product.slug == item["slug"]))
        if existing:
            continue
        db.add(Product(**item, enabled=True, provider="tgstars"))
    if not db.get(SystemSetting, "seeded"):
        db.add(SystemSetting(key="seeded", value="1"))
    db.commit()
