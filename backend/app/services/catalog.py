from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import apply_markup, money, percent_of
from app.integrations.tgstars.service import TgStarsService
from app.models import Mirror, Product
from app.services.marketplace import Marketplace

RENT_KINDS = {"nft_rent", "username_rent", "number_rent", "nft_buy"}


def load_mirror(db: Session, mirror_id: int | None) -> Mirror | None:
    if not mirror_id:
        return None
    return db.get(Mirror, mirror_id)


def _priced(provider_unit: Decimal, qty: int, mirror: Mirror | None, source: str, product: Product) -> dict:
    markup_percent = mirror.markup_percent if mirror else Decimal("0")
    markup_fixed = mirror.markup_fixed if mirror else Decimal("0")
    unit = apply_markup(provider_unit, markup_percent, markup_fixed)
    provider_total = money(provider_unit * qty)
    total = money(unit * qty)
    markup_amount = money(total - provider_total)
    commission = percent_of(markup_amount, mirror.commission_percent) if mirror else money(0)
    profit = money(markup_amount - commission)
    return {
        "product_id": product.id,
        "quantity": qty,
        "unit_price": unit,
        "provider_unit": provider_unit,
        "provider_cost": provider_total,
        "markup_amount": markup_amount,
        "commission_amount": commission,
        "profit": profit,
        "total": total,
        "currency": "RUB",
        "source": source,
        "min_quantity": product.min_quantity,
        "max_quantity": product.max_quantity,
    }


def quote_product(
    db: Session,
    product: Product,
    quantity: int,
    mirror: Mirror | None,
    tgstars: TgStarsService,
    *,
    nft_address: str | None = None,
) -> dict:
    qty = max(product.min_quantity, min(quantity, product.max_quantity))
    if product.kind == "stars":
        quote = tgstars.quote_stars(qty)
        return _priced(money(quote["unit_price"]), quote["quantity"], mirror, quote["source"], product)
    if product.kind in RENT_KINDS and nft_address:
        market = Marketplace()
        q = market.quote(product.kind, nft_address, qty)
        priced = _priced(money(q["unit_price"]), q["quantity"], mirror, q["source"], product)
        priced["name"] = q.get("name")
        priced["address"] = nft_address
        priced["available"] = q.get("available")
        return priced
    return _priced(money(product.fallback_unit_price), qty, mirror, "local", product)


def list_products(db: Session, *, q: str | None = None, category: str | None = None, only_enabled: bool = True):
    stmt = select(Product)
    if only_enabled:
        stmt = stmt.where(Product.enabled.is_(True))
    if category and category != "all":
        stmt = stmt.where(Product.category == category)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Product.name.ilike(like) | Product.description.ilike(like) | Product.category.ilike(like))
    stmt = stmt.order_by(Product.sort_order, Product.id)
    return list(db.scalars(stmt))
