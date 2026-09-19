from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.serializers import product_public
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.integrations.tgstars.service import TgStarsService
from app.models import Product, User
from app.services.catalog import list_products, load_mirror, quote_product

router = APIRouter(tags=["catalog"])
tgstars = TgStarsService()


class QuoteIn(BaseModel):
    product_id: int
    quantity: int


@router.get("/catalog")
def catalog(
    q: str | None = None,
    category: str | None = None,
    sort: str = "popular",
    price_min: float | None = None,
    price_max: float | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    products = list_products(db, q=q, category=category)
    mirror = load_mirror(db, user.mirror_id)
    items = []
    for product in products:
        qty = product.min_quantity
        quote = quote_product(db, product, qty, mirror, tgstars)
        item = product_public(product, unit_price=quote["unit_price"], total=quote["total"])
        item["quantity"] = quote["quantity"]
        items.append(item)
    if price_min is not None:
        items = [i for i in items if float(i.get("preview_total") or 0) >= price_min]
    if price_max is not None:
        items = [i for i in items if float(i.get("preview_total") or 0) <= price_max]
    if sort == "price_asc":
        items.sort(key=lambda x: float(x.get("unit_price") or 0))
    elif sort == "price_desc":
        items.sort(key=lambda x: float(x.get("unit_price") or 0), reverse=True)
    elif sort == "new":
        items.sort(key=lambda x: x["id"], reverse=True)
    return {"success": True, "data": {"items": items, "categories": ["stars", "premium", "nft", "username", "number"]}}


@router.get("/products/{product_id}")
def product_detail(product_id: int, quantity: int = Query(default=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise NotFoundError("Товар не найден")
    mirror = load_mirror(db, user.mirror_id)
    quote = quote_product(db, product, quantity, mirror, tgstars)
    data = product_public(product, unit_price=quote["unit_price"], total=quote["total"])
    data.update({k: (str(v) if hasattr(v, "quantize") else v) for k, v in quote.items() if k not in {"product_id"}})
    data["presets"] = [50, 100, 250, 500, 1000, 5000, 10000] if product.kind == "stars" else [product.min_quantity]
    return {"success": True, "data": data}


@router.post("/catalog/quote")
def quote(body: QuoteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(Product, body.product_id)
    if not product:
        raise NotFoundError("Товар не найден")
    mirror = load_mirror(db, user.mirror_id)
    quote = quote_product(db, product, body.quantity, mirror, tgstars)
    return {"success": True, "data": {k: (str(v) if hasattr(v, "quantize") else v) for k, v in quote.items()}}
