from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.db.session import get_db
from app.models import Order, Product, User
from app.services.marketplace import Marketplace
from app.services.processors import get_processor

router = APIRouter(tags=["rent"])
market = Marketplace()

KIND_SLUG = {
    "nft_rent": "nft-rent",
    "username_rent": "username-rent",
    "number_rent": "number-rent",
    "nft_buy": "nft-buy",
}


def _dec(data: dict) -> dict:
    out = {}
    for k, v in data.items():
        out[k] = str(v) if hasattr(v, "quantize") else v
    return out


@router.get("/rent/nft/collections")
def nft_collections(_: User = Depends(get_current_user)):
    return {"success": True, "data": market.nft_collections()}


@router.get("/rent/nft/list")
def nft_list(
    collection_address: str | None = None,
    q: str | None = None,
    sort_by: str | None = None,
    model: str | None = None,
    symbol: str | None = None,
    backdrop: str | None = None,
    cursor: str | None = None,
    _: User = Depends(get_current_user),
):
    return {
        "success": True,
        "data": market.nft_list(
            collection_address,
            q,
            sort_by=sort_by,
            model=model,
            symbol=symbol,
            backdrop=backdrop,
            cursor=cursor,
        ),
    }


@router.get("/rent/username/list")
def username_list(
    q: str | None = None,
    length_filter: list[int] | None = Query(None),
    numbers_filter: str | None = None,
    underscore_filter: str | None = None,
    sort_by: str | None = None,
    cursor: str | None = None,
    _: User = Depends(get_current_user),
):
    return {
        "success": True,
        "data": market.username_list(
            q,
            length_filter=length_filter,
            numbers_filter=numbers_filter,
            underscore_filter=underscore_filter,
            sort_by=sort_by,
            cursor=cursor,
        ),
    }


@router.get("/rent/number/list")
def number_list(
    length: str | None = None,
    sort_by: str | None = None,
    cursor: str | None = None,
    _: User = Depends(get_current_user),
):
    return {"success": True, "data": market.number_list(length=length, sort_by=sort_by, cursor=cursor)}


@router.get("/nft/buy/collections")
def buy_collections(_: User = Depends(get_current_user)):
    return {"success": True, "data": market.nft_buy_collections()}


@router.get("/nft/buy/list")
def buy_list(
    collection_address: str | None = None,
    sort_order: str | None = None,
    model: str | None = None,
    symbol: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    cursor: str | None = None,
    _: User = Depends(get_current_user),
):
    return {
        "success": True,
        "data": market.nft_buy_list(
            collection_address,
            sort_order=sort_order,
            model=model,
            symbol=symbol,
            min_price=min_price,
            max_price=max_price,
            cursor=cursor,
        ),
    }


@router.get("/nft/buy/info")
def buy_info(nft_address: str, _: User = Depends(get_current_user)):
    info = market.nft_buy_info(nft_address)
    if not info:
        raise NotFoundError("NFT не найден")
    return {"success": True, "data": info}


@router.get("/rent/quote")
def rent_quote(
    kind: str = Query(...),
    address: str = Query(...),
    days: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if kind not in KIND_SLUG:
        raise AppError("INVALID_KIND", "Неизвестный тип лота")
    data = _dec(market.quote(kind, address, days))
    product = db.scalar(select(Product).where(Product.slug == KIND_SLUG[kind]))
    if product:
        data["product_id"] = product.id
    return {"success": True, "data": data}


class ConnectIn(BaseModel):
    order_id: int
    tonconnect_url: str = Field(min_length=4, max_length=500)


@router.post("/rent/connect")
def rent_connect(body: ConnectIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.get(Order, body.order_id)
    if not order or order.user_id != user.id:
        raise NotFoundError("Заказ не найден")
    if (order.payload or {}).get("kind") not in {"nft_rent", "username_rent", "number_rent"}:
        raise AppError("INVALID_KIND", "TON Connect только для аренды")
    settings = get_settings()
    payload = dict(order.payload or {})
    payload["tonconnect_url"] = "stored"
    if settings.demo_mode or not settings.tgstars_enabled:
        payload["connect"] = "demo"
        order.payload = payload
        db.commit()
        return {"success": True, "data": {"connected": True, "demo": True, "nft_address": order.recipient}}
    processor = get_processor()
    if hasattr(processor, "client"):
        result = processor.client.rent_connect(int(order.provider_order_id or 0), body.tonconnect_url)
        payload["connect"] = result
        order.payload = payload
        db.commit()
        return {"success": True, "data": result}
    raise AppError("UNAVAILABLE", "Connect недоступен")


class TransferIn(BaseModel):
    order_id: int
    destination: str = Field(pattern="^(telegram|wallet)$")
    username: str | None = None
    wallet_address: str | None = None


@router.post("/nft/transfer")
def nft_transfer(body: TransferIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.get(Order, body.order_id)
    if not order or order.user_id != user.id:
        raise NotFoundError("Заказ не найден")
    if (order.payload or {}).get("kind") not in {"nft_buy", "nft_rent"}:
        raise AppError("INVALID_KIND", "Перевод только для NFT")
    settings = get_settings()
    payload = dict(order.payload or {})
    dest = (body.username or body.wallet_address or "").strip()
    if body.destination == "telegram":
        dest = (body.username or "").lstrip("@").strip()
        if len(dest) < 3:
            raise AppError("INVALID_RECIPIENT", "Укажите username")
    else:
        dest = (body.wallet_address or "").strip()
        if len(dest) < 10:
            raise AppError("INVALID_WALLET", "Укажите TON-адрес")
    if settings.demo_mode or not settings.tgstars_enabled:
        payload["transfer"] = {"destination": body.destination, "target": dest, "demo": True}
        order.payload = payload
        db.commit()
        return {"success": True, "data": {"transferred": True, "demo": True, "destination": body.destination, "target": dest}}
    processor = get_processor()
    if not hasattr(processor, "client"):
        raise AppError("UNAVAILABLE", "Перевод недоступен")
    tx_id = int(order.provider_order_id or 0)
    if body.destination == "telegram":
        result = processor.client.transfer_nft_telegram(tx_id, dest)
    else:
        result = processor.client.transfer_nft_wallet(tx_id, dest)
    payload["transfer"] = result
    order.payload = payload
    db.commit()
    return {"success": True, "data": result}
