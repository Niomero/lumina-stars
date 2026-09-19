from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.core.money import money
from app.db.session import get_db
from app.models import Product, User
from app.services import promos as promo_svc
from app.services.catalog import load_mirror, quote_product
from app.integrations.tgstars.service import TgStarsService

router = APIRouter(prefix="/promos", tags=["promos"])
tgstars = TgStarsService()


class RedeemIn(BaseModel):
    code: str = Field(min_length=3, max_length=32)


@router.get("/preview")
def preview_promo(
    code: str,
    product_id: int | None = None,
    quantity: int | None = Query(default=None, ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id) if product_id else None
    if product_id and not product:
        raise NotFoundError("Товар не найден")
    total = None
    if product:
        qty = quantity or product.min_quantity
        mirror = load_mirror(db, user.mirror_id)
        quote = quote_product(db, product, qty, mirror, tgstars)
        total = money(quote["total"])
    data = promo_svc.preview(db, user, code, product=product, total=total)
    return {"success": True, "data": data}


@router.post("/redeem")
def redeem_promo(body: RedeemIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = promo_svc.redeem_balance(db, user, body.code)
    return {"success": True, "data": data}
