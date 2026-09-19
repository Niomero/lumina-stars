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
    {
        "slug": "steam-topup",
        "name": "Steam пополнение",
        "description": "Пополнение кошелька Steam по логину. Укажите Steam логин и сумму — заказ уйдёт в обработку.",
        "category": "steam",
        "group": "topup",
        "region": "RU",
        "currency": "RUB",
        "face_value": "",
        "price": Decimal("0.00"),
        "delivery_type": "manual",
        "amount_mode": "custom",
        "markup_percent": Decimal("10.00"),
        "min_amount": Decimal("100.00"),
        "max_amount": Decimal("15000.00"),
        "sort_order": 1,
        "extra_fields": [{"key": "steam_login", "label": "Steam логин", "required": True}],
    },
    {"slug": "gplay-5-us", "name": "Google Play 5 USD", "description": "Gift card Google Play 5 USD.", "category": "google_play", "group": "topup", "region": "US", "currency": "USD", "face_value": "5", "price": Decimal("520.00"), "sort_order": 11},
    {"slug": "gplay-10-us", "name": "Google Play 10 USD", "description": "Gift card Google Play. Код придёт после оплаты.", "category": "google_play", "group": "topup", "region": "US", "currency": "USD", "face_value": "10", "price": Decimal("990.00"), "sort_order": 12},
    {"slug": "gplay-15-us", "name": "Google Play 15 USD", "description": "Gift card Google Play 15 USD.", "category": "google_play", "group": "topup", "region": "US", "currency": "USD", "face_value": "15", "price": Decimal("1480.00"), "sort_order": 13},
    {"slug": "gplay-25-us", "name": "Google Play 25 USD", "description": "Gift card Google Play 25 USD.", "category": "google_play", "group": "topup", "region": "US", "currency": "USD", "face_value": "25", "price": Decimal("2450.00"), "sort_order": 14},
    {"slug": "gplay-50-us", "name": "Google Play 50 USD", "description": "Gift card Google Play 50 USD.", "category": "google_play", "group": "topup", "region": "US", "currency": "USD", "face_value": "50", "price": Decimal("4890.00"), "sort_order": 15},
    {"slug": "appstore-5-us", "name": "App Store 5 USD", "description": "Код пополнения Apple / App Store.", "category": "app_store", "group": "topup", "region": "US", "currency": "USD", "face_value": "5", "price": Decimal("530.00"), "sort_order": 21},
    {"slug": "appstore-10-us", "name": "App Store 10 USD", "description": "Код пополнения Apple / App Store.", "category": "app_store", "group": "topup", "region": "US", "currency": "USD", "face_value": "10", "price": Decimal("1020.00"), "sort_order": 22},
    {"slug": "appstore-15-us", "name": "App Store 15 USD", "description": "Код App Store 15 USD.", "category": "app_store", "group": "topup", "region": "US", "currency": "USD", "face_value": "15", "price": Decimal("1520.00"), "sort_order": 23},
    {"slug": "appstore-25-us", "name": "App Store 25 USD", "description": "Код App Store 25 USD.", "category": "app_store", "group": "topup", "region": "US", "currency": "USD", "face_value": "25", "price": Decimal("2520.00"), "sort_order": 24},
    {"slug": "psn-10-us", "name": "PlayStation 10 USD", "description": "Карта пополнения PlayStation Store.", "category": "playstation", "group": "topup", "region": "US", "currency": "USD", "face_value": "10", "price": Decimal("1010.00"), "sort_order": 31},
    {"slug": "psn-25-us", "name": "PlayStation 25 USD", "description": "Карта PlayStation Store 25 USD.", "category": "playstation", "group": "topup", "region": "US", "currency": "USD", "face_value": "25", "price": Decimal("2490.00"), "sort_order": 32},
    {"slug": "psn-50-us", "name": "PlayStation 50 USD", "description": "Карта PlayStation Store 50 USD.", "category": "playstation", "group": "topup", "region": "US", "currency": "USD", "face_value": "50", "price": Decimal("4950.00"), "sort_order": 33},
    {"slug": "xbox-10-us", "name": "Xbox 10 USD", "description": "Код Microsoft / Xbox.", "category": "xbox", "group": "topup", "region": "US", "currency": "USD", "face_value": "10", "price": Decimal("990.00"), "sort_order": 41},
    {"slug": "xbox-25-us", "name": "Xbox 25 USD", "description": "Код Microsoft / Xbox 25 USD.", "category": "xbox", "group": "topup", "region": "US", "currency": "USD", "face_value": "25", "price": Decimal("2450.00"), "sort_order": 42},
    {"slug": "nintendo-10-us", "name": "Nintendo eShop 10 USD", "description": "Код Nintendo eShop.", "category": "nintendo", "group": "topup", "region": "US", "currency": "USD", "face_value": "10", "price": Decimal("1010.00"), "sort_order": 51},
    {"slug": "nintendo-35-us", "name": "Nintendo eShop 35 USD", "description": "Код Nintendo eShop 35 USD.", "category": "nintendo", "group": "topup", "region": "US", "currency": "USD", "face_value": "35", "price": Decimal("3490.00"), "sort_order": 52},
    {"slug": "spotify-1m", "name": "Spotify Premium 1 месяц", "description": "Код подписки Spotify Premium.", "category": "spotify", "group": "topup", "region": "GLOBAL", "currency": "USD", "face_value": "1 мес.", "price": Decimal("690.00"), "sort_order": 61},
    {"slug": "spotify-3m", "name": "Spotify Premium 3 месяца", "description": "Код подписки Spotify Premium на 3 месяца.", "category": "spotify", "group": "topup", "region": "GLOBAL", "currency": "USD", "face_value": "3 мес.", "price": Decimal("1890.00"), "sort_order": 62},
    {"slug": "roblox-400", "name": "Roblox 400 Robux", "description": "Robux на аккаунт. Укажите Roblox username.", "category": "roblox", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "400", "price": Decimal("490.00"), "sort_order": 71, "extra_fields": [{"key": "username", "label": "Roblox Username", "required": True}]},
    {"slug": "roblox-800", "name": "Roblox 800 Robux", "description": "Цифровой код Roblox. Укажите username перед оплатой.", "category": "roblox", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "800", "price": Decimal("890.00"), "sort_order": 72, "extra_fields": [{"key": "username", "label": "Roblox Username", "required": True}]},
    {"slug": "roblox-1700", "name": "Roblox 1700 Robux", "description": "Robux на аккаунт. Укажите Roblox username.", "category": "roblox", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "1700", "price": Decimal("1790.00"), "sort_order": 73, "extra_fields": [{"key": "username", "label": "Roblox Username", "required": True}]},
    {"slug": "roblox-4500", "name": "Roblox 4500 Robux", "description": "Robux на аккаунт. Укажите Roblox username.", "category": "roblox", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "4500", "price": Decimal("4490.00"), "sort_order": 74, "extra_fields": [{"key": "username", "label": "Roblox Username", "required": True}]},
    {"slug": "roblox-10000", "name": "Roblox 10000 Robux", "description": "Robux на аккаунт. Укажите Roblox username.", "category": "roblox", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "10000", "price": Decimal("9790.00"), "sort_order": 75, "extra_fields": [{"key": "username", "label": "Roblox Username", "required": True}]},
    {"slug": "minecraft-java", "name": "Minecraft Java Edition", "description": "Ключ Minecraft Java Edition. Можно указать ник.", "category": "minecraft", "group": "games", "region": "GLOBAL", "currency": "EUR", "face_value": "Java", "price": Decimal("2490.00"), "sort_order": 81, "extra_fields": [{"key": "username", "label": "Minecraft username", "required": False}]},
    {"slug": "minecraft-bedrock", "name": "Minecraft Bedrock", "description": "Код Minecraft Bedrock Edition.", "category": "minecraft", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "Bedrock", "price": Decimal("1490.00"), "sort_order": 82, "extra_fields": [{"key": "username", "label": "Gamertag", "required": False}]},
    {"slug": "minecraft-10", "name": "Minecraft 10 EUR", "description": "Карта / код Minecraft 10 EUR.", "category": "minecraft", "group": "games", "region": "EU", "currency": "EUR", "face_value": "10", "price": Decimal("990.00"), "sort_order": 83, "extra_fields": [{"key": "username", "label": "Minecraft username", "required": False}]},
    {"slug": "minecraft-20", "name": "Minecraft 20 EUR", "description": "Код пополнения / карты Minecraft.", "category": "minecraft", "group": "games", "region": "EU", "currency": "EUR", "face_value": "20", "price": Decimal("1890.00"), "sort_order": 84, "extra_fields": [{"key": "username", "label": "Minecraft username", "required": False}]},
    {"slug": "minecraft-coins-1720", "name": "Minecraft 1720 Minecoins", "description": "Minecoins для Marketplace.", "category": "minecraft", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "1720", "price": Decimal("1290.00"), "sort_order": 85, "extra_fields": [{"key": "username", "label": "Gamertag", "required": False}]},
    {"slug": "minecraft-coins-3500", "name": "Minecraft 3500 Minecoins", "description": "Minecoins для Marketplace.", "category": "minecraft", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "3500", "price": Decimal("2490.00"), "sort_order": 86, "extra_fields": [{"key": "username", "label": "Gamertag", "required": False}]},
    {"slug": "minecraft-realms", "name": "Minecraft Realms 30 дней", "description": "Код подписки Minecraft Realms.", "category": "minecraft", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "30 дней", "price": Decimal("890.00"), "sort_order": 87, "extra_fields": [{"key": "username", "label": "Minecraft username", "required": False}]},
    {"slug": "fortnite-1000", "name": "Fortnite 1000 V-Bucks", "description": "V-Bucks. Укажите Epic username.", "category": "fortnite", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "1000", "price": Decimal("890.00"), "sort_order": 91, "extra_fields": [{"key": "username", "label": "Epic username", "required": True}]},
    {"slug": "fortnite-2800", "name": "Fortnite 2800 V-Bucks", "description": "V-Bucks. Укажите Epic username.", "category": "fortnite", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "2800", "price": Decimal("2190.00"), "sort_order": 92, "extra_fields": [{"key": "username", "label": "Epic username", "required": True}]},
    {"slug": "fortnite-5000", "name": "Fortnite 5000 V-Bucks", "description": "V-Bucks. Укажите Epic username.", "category": "fortnite", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "5000", "price": Decimal("3490.00"), "sort_order": 93, "extra_fields": [{"key": "username", "label": "Epic username", "required": True}]},
    {"slug": "valorant-1000", "name": "Valorant 1000 VP", "description": "Valorant Points. Укажите Riot ID.", "category": "valorant", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "1000", "price": Decimal("890.00"), "sort_order": 101, "extra_fields": [{"key": "username", "label": "Riot ID", "required": True}]},
    {"slug": "valorant-2050", "name": "Valorant 2050 VP", "description": "Valorant Points. Укажите Riot ID.", "category": "valorant", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "2050", "price": Decimal("1690.00"), "sort_order": 102, "extra_fields": [{"key": "username", "label": "Riot ID", "required": True}]},
    {"slug": "valorant-3650", "name": "Valorant 3650 VP", "description": "Valorant Points. Укажите Riot ID.", "category": "valorant", "group": "games", "region": "GLOBAL", "currency": "USD", "face_value": "3650", "price": Decimal("2790.00"), "sort_order": 103, "extra_fields": [{"key": "username", "label": "Riot ID", "required": True}]},
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
        extra = item.get("extra_fields")
        payload = {k: v for k, v in item.items() if k != "extra_fields"}
        db.add(
            DigitalProduct(
                **payload,
                extra_fields=extra,
                provider="inventory",
                enabled=True,
            )
        )
    for slug in ("steam-500-ru", "steam-1000-ru"):
        old = db.scalar(select(DigitalProduct).where(DigitalProduct.slug == slug))
        if old and old.enabled:
            old.enabled = False
    if not db.get(SystemSetting, "seeded"):
        db.add(SystemSetting(key="seeded", value="1"))
    owner_id = int(get_settings().owner_telegram_id or 0)
    if owner_id:
        owner = db.scalar(select(User).where(User.telegram_id == owner_id))
        if owner and owner.role != Role.SUPERADMIN.value:
            owner.role = Role.SUPERADMIN.value
    db.commit()
