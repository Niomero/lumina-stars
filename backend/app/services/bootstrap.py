from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rbac import Role
from app.models import DigitalProduct, Product, SystemSetting, User


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
        "fallback_unit_price": Decimal("1.32"),
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
    {
        "slug": "nft-rent",
        "name": "Аренда NFT-подарка",
        "description": "Аренда Telegram Gift NFT на выбранный срок. В DEMO без блокчейн-операции.",
        "category": "nft",
        "icon": "gift",
        "kind": "nft_rent",
        "provider_product_id": "rent-nft",
        "min_quantity": 1,
        "max_quantity": 90,
        "step": 1,
        "fallback_unit_price": Decimal("18.00"),
        "popular": True,
        "sort_order": 10,
    },
    {
        "slug": "username-rent",
        "name": "Аренда Username",
        "description": "Аренда коллекционного Telegram username.",
        "category": "username",
        "icon": "at-sign",
        "kind": "username_rent",
        "provider_product_id": "rent-username",
        "min_quantity": 7,
        "max_quantity": 365,
        "step": 1,
        "fallback_unit_price": Decimal("48.00"),
        "popular": True,
        "sort_order": 11,
    },
    {
        "slug": "number-rent",
        "name": "Аренда номера",
        "description": "Аренда анонимного Telegram-номера.",
        "category": "number",
        "icon": "hash",
        "kind": "number_rent",
        "provider_product_id": "rent-number",
        "min_quantity": 7,
        "max_quantity": 180,
        "step": 1,
        "fallback_unit_price": Decimal("52.00"),
        "popular": False,
        "sort_order": 12,
    },
    {
        "slug": "nft-buy",
        "name": "Покупка NFT-подарка",
        "description": "Покупка Gift NFT. В DEMO без on-chain перевода.",
        "category": "nft",
        "icon": "gem",
        "kind": "nft_buy",
        "provider_product_id": "buy-nft",
        "min_quantity": 1,
        "max_quantity": 1,
        "step": 1,
        "fallback_unit_price": Decimal("1420.00"),
        "popular": True,
        "sort_order": 13,
    },
]


DIGITAL = [
    {"slug": "steam-500-ru", "name": "Steam 500 ₽", "description": "Пополнение кошелька Steam на 500 ₽. После оплаты вы получите код.", "category": "steam", "group": "topup", "region": "RU", "currency": "RUB", "face_value": "500", "price": Decimal("549.00"), "sort_order": 1},
    {"slug": "steam-1000-ru", "name": "Steam 1000 ₽", "description": "Пополнение кошелька Steam на 1000 ₽.", "category": "steam", "group": "topup", "region": "RU", "currency": "RUB", "face_value": "1000", "price": Decimal("1089.00"), "sort_order": 2},
    {"slug": "gplay-10-us", "name": "Google Play 10 USD", "description": "Gift card Google Play. Код придёт после оплаты.", "category": "google_play", "group": "topup", "region": "US", "currency": "USD", "face_value": "10", "price": Decimal("990.00"), "sort_order": 3},
    {"slug": "gplay-25-us", "name": "Google Play 25 USD", "description": "Gift card Google Play 25 USD.", "category": "google_play", "group": "topup", "region": "US", "currency": "USD", "face_value": "25", "price": Decimal("2450.00"), "sort_order": 4},
    {"slug": "appstore-10-us", "name": "App Store 10 USD", "description": "Код пополнения Apple / App Store.", "category": "app_store", "group": "topup", "region": "US", "currency": "USD", "face_value": "10", "price": Decimal("1020.00"), "sort_order": 5},
    {"slug": "psn-10-us", "name": "PlayStation 10 USD", "description": "Карта пополнения PlayStation Store.", "category": "playstation", "group": "topup", "region": "US", "currency": "USD", "face_value": "10", "price": Decimal("1010.00"), "sort_order": 6},
    {"slug": "xbox-10-us", "name": "Xbox 10 USD", "description": "Код Microsoft / Xbox.", "category": "xbox", "group": "topup", "region": "US", "currency": "USD", "face_value": "10", "price": Decimal("990.00"), "sort_order": 7},
    {"slug": "nintendo-10-us", "name": "Nintendo eShop 10 USD", "description": "Код Nintendo eShop.", "category": "nintendo", "group": "topup", "region": "US", "currency": "USD", "face_value": "10", "price": Decimal("1010.00"), "sort_order": 8},
    {"slug": "roblox-800", "name": "Roblox 800 Robux", "description": "Цифровой код Roblox. Укажите username перед оплатой.", "category": "roblox", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "800", "price": Decimal("890.00"), "sort_order": 9, "extra_fields": [{"key": "username", "label": "Roblox Username", "required": True}]},
    {"slug": "minecraft-20", "name": "Minecraft 20 EUR", "description": "Код пополнения / карты Minecraft.", "category": "minecraft", "group": "games", "region": "EU", "currency": "EUR", "face_value": "20", "price": Decimal("1890.00"), "sort_order": 10, "extra_fields": [{"key": "username", "label": "Minecraft username", "required": False}]},
]


def seed(db: Session) -> None:
    for item in PRODUCTS:
        existing = db.scalar(select(Product).where(Product.slug == item["slug"]))
        if existing:
            if item["slug"] == "telegram-stars" and existing.fallback_unit_price != item["fallback_unit_price"]:
                existing.fallback_unit_price = item["fallback_unit_price"]
            continue
        db.add(Product(**item, enabled=True, provider="tgstars"))
    for item in DIGITAL:
        if db.scalar(select(DigitalProduct.id).where(DigitalProduct.slug == item["slug"])):
            continue
        payload = {k: v for k, v in item.items() if k != "extra_fields"}
        db.add(
            DigitalProduct(
                **payload,
                extra_fields=item.get("extra_fields"),
                provider="inventory",
                delivery_type="code",
                enabled=True,
            )
        )
    if not db.get(SystemSetting, "seeded"):
        db.add(SystemSetting(key="seeded", value="1"))
    owner_id = int(get_settings().owner_telegram_id or 0)
    if owner_id:
        owner = db.scalar(select(User).where(User.telegram_id == owner_id))
        if owner and owner.role != Role.SUPERADMIN.value:
            owner.role = Role.SUPERADMIN.value
    db.commit()
