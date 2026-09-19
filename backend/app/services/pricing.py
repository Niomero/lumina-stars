from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.money import money, percent_of
from app.models import Sale, SystemSetting

CATS = ("stars", "premium", "nft", "username", "number")
KIND_CAT = {
    "stars": "stars",
    "premium": "premium",
    "nft_rent": "nft",
    "nft_buy": "nft",
    "username_rent": "username",
    "number_rent": "number",
}

_SNAP: tuple[float, "PriceBook"] | None = None
TTL = 12.0


def category_of(kind: str | None, category: str | None = None) -> str:
    if category in CATS:
        return category
    return KIND_CAT.get(kind or "", "stars")


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_admin_password(password: str) -> str:
    secret = get_settings().secret_key.encode()
    return hashlib.sha256(secret + b"::admin::" + (password or "").encode()).hexdigest()


def admin_password_ok(db: Session, password: str) -> bool:
    stored = db.get(SystemSetting, "admin_password_hash")
    if stored and stored.value:
        return hmac.compare_digest(stored.value, hash_admin_password(password))
    expected = get_settings().admin_password
    return hmac.compare_digest(password or "", expected)


def set_admin_password(db: Session, password: str) -> None:
    if len(password or "") < 8:
        from app.core.errors import AppError

        raise AppError("WEAK_PASSWORD", "Пароль не короче 8 символов")
    row = db.get(SystemSetting, "admin_password_hash")
    digest = hash_admin_password(password)
    if row:
        row.value = digest
    else:
        db.add(SystemSetting(key="admin_password_hash", value=digest))


@dataclass
class ActiveSale:
    id: int
    name: str
    percent: Decimal
    categories: set[str]


@dataclass
class PriceBook:
    global_percent: Decimal = Decimal("0")
    by_cat: dict[str, Decimal | None] = field(default_factory=dict)
    sales: list[ActiveSale] = field(default_factory=list)

    def markup_for(self, category: str) -> Decimal:
        own = self.by_cat.get(category)
        if own is not None:
            return money(own)
        return money(self.global_percent)

    def sale_for(self, category: str) -> ActiveSale | None:
        best = None
        for sale in self.sales:
            if "all" in sale.categories or category in sale.categories:
                if best is None or sale.percent > best.percent:
                    best = sale
        return best

    def apply(self, api_amount, *, kind: str | None = None, category: str | None = None) -> dict:
        api = money(api_amount)
        cat = category_of(kind, category)
        markup = self.markup_for(cat)
        listed = money(api + percent_of(api, markup))
        sale = self.sale_for(cat)
        final = listed
        sale_percent = money(0)
        sale_name = None
        if sale and sale.percent > 0:
            sale_percent = money(sale.percent)
            final = money(listed - percent_of(listed, sale_percent))
            sale_name = sale.name
        if final < 0:
            final = money(0)
        return {
            "api": api,
            "listed": listed,
            "unit": final,
            "markup_percent": markup,
            "sale_percent": sale_percent,
            "sale_name": sale_name,
            "compare_at": listed if sale_percent > 0 and listed > final else None,
            "category": cat,
        }


def _setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(SystemSetting, key)
    return row.value if row and row.value is not None else default


def _parse_percent(raw: str | None) -> Decimal | None:
    if raw is None or str(raw).strip() == "":
        return None
    return money(raw)


def load_book(db: Session) -> PriceBook:
    global_p = _parse_percent(_setting(db, "price_percent", "0")) or money(0)
    by_cat: dict[str, Decimal | None] = {}
    for cat in CATS:
        by_cat[cat] = _parse_percent(_setting(db, f"price_percent_{cat}", ""))
    now = _now()
    sales: list[ActiveSale] = []
    for row in db.scalars(select(Sale).where(Sale.enabled.is_(True))):
        starts = _aware(row.starts_at)
        expires = _aware(row.expires_at)
        if starts and now < starts:
            continue
        if expires and now > expires:
            continue
        cats = {c.strip() for c in (row.categories or "all").split(",") if c.strip()} or {"all"}
        sales.append(ActiveSale(id=row.id, name=row.name, percent=money(row.percent), categories=cats))
    return PriceBook(global_percent=global_p, by_cat=by_cat, sales=sales)


def refresh_pricing(db: Session) -> PriceBook:
    global _SNAP
    book = load_book(db)
    _SNAP = (time.time(), book)
    try:
        from app.services.marketplace import clear_cache

        clear_cache()
    except Exception:
        pass
    return book


def clear_pricing_cache() -> None:
    global _SNAP
    _SNAP = None


def current_book(db: Session | None = None) -> PriceBook:
    global _SNAP
    now = time.time()
    if _SNAP and now - _SNAP[0] < TTL:
        return _SNAP[1]
    if db is not None:
        try:
            return refresh_pricing(db)
        except Exception:
            return PriceBook()
    try:
        from app.db.session import SessionLocal

        session = SessionLocal()
        try:
            return refresh_pricing(session)
        finally:
            session.close()
    except Exception:
        book = PriceBook()
        _SNAP = (now, book)
        return book


def shop_price(api_amount, *, kind: str | None = None, category: str | None = None, db: Session | None = None) -> dict:
    return current_book(db).apply(api_amount, kind=kind, category=category)


def sale_public(row: Sale) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "percent": f"{money(row.percent):.2f}",
        "categories": row.categories,
        "enabled": row.enabled,
        "starts_at": row.starts_at.isoformat() if row.starts_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "note": row.note or "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def pricing_public(db: Session) -> dict:
    book = current_book(db)
    return {
        "global_percent": f"{book.global_percent:.2f}",
        "categories": {cat: (None if book.by_cat.get(cat) is None else f"{book.by_cat[cat]:.2f}") for cat in CATS},
        "active_sales": [
            {"id": s.id, "name": s.name, "percent": f"{s.percent:.2f}", "categories": sorted(s.categories)}
            for s in book.sales
        ],
    }


def upsert_setting(db: Session, key: str, value: str) -> None:
    row = db.get(SystemSetting, key)
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
