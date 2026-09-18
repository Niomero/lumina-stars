from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.money import money
from app.integrations.tgstars.client import TgStarsClient
from app.integrations.tgstars.exceptions import TgStarsError

DEMO_COLLECTIONS = [
    {"address": "EQ-gifts-classic", "name": "Classic Gifts", "count": 10, "kind": "nft"},
    {"address": "EQ-gifts-luxe", "name": "Luxe Gifts", "count": 8, "kind": "nft"},
]

DEMO_NFTS = [
    {"address": "EQ-plush-pepe", "name": "Plush Pepe", "collection": "EQ-gifts-luxe", "collection_name": "Luxe Gifts", "price_per_day": "86.00", "buy_price": "12400.00", "min_days": 1, "max_days": 30, "tone": 142, "motif": "pepe", "model": "Plush", "symbol": "Pepe"},
    {"address": "EQ-eternal-rose", "name": "Eternal Rose", "collection": "EQ-gifts-luxe", "collection_name": "Luxe Gifts", "price_per_day": "42.00", "buy_price": "4800.00", "min_days": 1, "max_days": 60, "tone": 352, "motif": "rose", "model": "Eternal", "symbol": "Rose"},
    {"address": "EQ-signet-ring", "name": "Signet Ring", "collection": "EQ-gifts-luxe", "collection_name": "Luxe Gifts", "price_per_day": "58.00", "buy_price": "6900.00", "min_days": 1, "max_days": 45, "tone": 38, "motif": "ring", "model": "Signet", "symbol": "Ring"},
    {"address": "EQ-precious-peach", "name": "Precious Peach", "collection": "EQ-gifts-luxe", "collection_name": "Luxe Gifts", "price_per_day": "37.00", "buy_price": "4100.00", "min_days": 1, "max_days": 60, "tone": 18, "motif": "peach", "model": "Precious", "symbol": "Peach"},
    {"address": "EQ-loot-bag", "name": "Loot Bag", "collection": "EQ-gifts-luxe", "collection_name": "Luxe Gifts", "price_per_day": "29.00", "buy_price": "2650.00", "min_days": 1, "max_days": 90, "tone": 48, "motif": "bag", "model": "Loot", "symbol": "Bag"},
    {"address": "EQ-spiced-wine", "name": "Spiced Wine", "collection": "EQ-gifts-luxe", "collection_name": "Luxe Gifts", "price_per_day": "24.00", "buy_price": "1980.00", "min_days": 1, "max_days": 90, "tone": 8, "motif": "wine", "model": "Spiced", "symbol": "Wine"},
    {"address": "EQ-diamond-ring", "name": "Diamond Ring", "collection": "EQ-gifts-luxe", "collection_name": "Luxe Gifts", "price_per_day": "94.00", "buy_price": "15800.00", "min_days": 1, "max_days": 30, "tone": 210, "motif": "diamond", "model": "Diamond", "symbol": "Ring"},
    {"address": "EQ-vintage-cigar", "name": "Vintage Cigar", "collection": "EQ-gifts-luxe", "collection_name": "Luxe Gifts", "price_per_day": "33.00", "buy_price": "3200.00", "min_days": 1, "max_days": 60, "tone": 28, "motif": "cigar", "model": "Vintage", "symbol": "Cigar"},
    {"address": "EQ-homemade-cake", "name": "Homemade Cake", "collection": "EQ-gifts-classic", "collection_name": "Classic Gifts", "price_per_day": "12.50", "buy_price": "890.00", "min_days": 1, "max_days": 90, "tone": 28, "motif": "cake", "model": "Homemade", "symbol": "Cake"},
    {"address": "EQ-green-star", "name": "Green Star", "collection": "EQ-gifts-classic", "collection_name": "Classic Gifts", "price_per_day": "18.00", "buy_price": "1420.00", "min_days": 1, "max_days": 90, "tone": 128, "motif": "star", "model": "Classic", "symbol": "Star"},
    {"address": "EQ-blue-star", "name": "Blue Star", "collection": "EQ-gifts-classic", "collection_name": "Classic Gifts", "price_per_day": "18.00", "buy_price": "1420.00", "min_days": 1, "max_days": 90, "tone": 212, "motif": "star", "model": "Classic", "symbol": "Star"},
    {"address": "EQ-teddy-bear", "name": "Teddy Bear", "collection": "EQ-gifts-classic", "collection_name": "Classic Gifts", "price_per_day": "16.00", "buy_price": "1180.00", "min_days": 1, "max_days": 90, "tone": 24, "motif": "teddy", "model": "Classic", "symbol": "Bear"},
    {"address": "EQ-cookie-heart", "name": "Cookie Heart", "collection": "EQ-gifts-classic", "collection_name": "Classic Gifts", "price_per_day": "11.00", "buy_price": "740.00", "min_days": 1, "max_days": 90, "tone": 4, "motif": "heart", "model": "Classic", "symbol": "Heart"},
    {"address": "EQ-ice-cream", "name": "Ice Cream", "collection": "EQ-gifts-classic", "collection_name": "Classic Gifts", "price_per_day": "9.50", "buy_price": "620.00", "min_days": 1, "max_days": 90, "tone": 188, "motif": "ice", "model": "Classic", "symbol": "Ice"},
    {"address": "EQ-delicious-cake", "name": "Delicious Cake", "collection": "EQ-gifts-classic", "collection_name": "Classic Gifts", "price_per_day": "10.00", "buy_price": "680.00", "min_days": 1, "max_days": 90, "tone": 332, "motif": "cake", "model": "Classic", "symbol": "Cake"},
    {"address": "EQ-red-star", "name": "Red Star", "collection": "EQ-gifts-classic", "collection_name": "Classic Gifts", "price_per_day": "18.00", "buy_price": "1420.00", "min_days": 1, "max_days": 90, "tone": 0, "motif": "star", "model": "Classic", "symbol": "Star"},
    {"address": "EQ-bento-box", "name": "Bento Box", "collection": "EQ-gifts-classic", "collection_name": "Classic Gifts", "price_per_day": "14.00", "buy_price": "980.00", "min_days": 1, "max_days": 90, "tone": 42, "motif": "bento", "model": "Classic", "symbol": "Box"},
    {"address": "EQ-crystal-ball", "name": "Crystal Ball", "collection": "EQ-gifts-classic", "collection_name": "Classic Gifts", "price_per_day": "21.00", "buy_price": "1680.00", "min_days": 1, "max_days": 90, "tone": 262, "motif": "crystal", "model": "Classic", "symbol": "Ball"},
]

DEMO_USERNAMES = [
    {"address": "EQ-user-lume", "name": "lume", "price_per_day": "64.00", "min_days": 7, "max_days": 365, "length": 4},
    {"address": "EQ-user-nova", "name": "nova", "price_per_day": "71.00", "min_days": 7, "max_days": 365, "length": 4},
    {"address": "EQ-user-silk", "name": "silk", "price_per_day": "48.00", "min_days": 7, "max_days": 365, "length": 4},
    {"address": "EQ-user-orbit", "name": "orbit", "price_per_day": "39.00", "min_days": 7, "max_days": 365, "length": 5},
    {"address": "EQ-user-atelier", "name": "atelier", "price_per_day": "28.00", "min_days": 7, "max_days": 365, "length": 7},
    {"address": "EQ-user-mercury", "name": "mercury", "price_per_day": "33.00", "min_days": 7, "max_days": 365, "length": 7},
    {"address": "EQ-user-aria", "name": "aria", "price_per_day": "82.00", "min_days": 7, "max_days": 365, "length": 4},
    {"address": "EQ-user-quartz", "name": "quartz", "price_per_day": "31.00", "min_days": 7, "max_days": 365, "length": 6},
]

DEMO_NUMBERS = [
    {"address": "EQ-num-8881", "name": "+888 12 34", "price_per_day": "52.00", "min_days": 7, "max_days": 180, "digits": "1234"},
    {"address": "EQ-num-8882", "name": "+888 77 77", "price_per_day": "96.00", "min_days": 7, "max_days": 180, "digits": "7777"},
    {"address": "EQ-num-8883", "name": "+888 00 01", "price_per_day": "41.00", "min_days": 7, "max_days": 180, "digits": "0001"},
    {"address": "EQ-num-8884", "name": "+888 42 42", "price_per_day": "58.00", "min_days": 7, "max_days": 180, "digits": "4242"},
    {"address": "EQ-num-8885", "name": "+888 10 01", "price_per_day": "44.00", "min_days": 7, "max_days": 180, "digits": "1001"},
    {"address": "EQ-num-8886", "name": "+888 88 88", "price_per_day": "128.00", "min_days": 7, "max_days": 180, "digits": "8888"},
]


def _motif_of(name: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    n = (name or "").lower()
    for key in ("pepe", "rose", "ring", "peach", "bag", "wine", "diamond", "cigar", "cake", "star", "teddy", "heart", "ice", "bento", "crystal"):
        if key in n:
            return key
    return "gift"


def _item(kind: str, raw: dict, extra: dict | None = None) -> dict:
    addr = str(raw.get("nft_address") or raw.get("address") or raw.get("id") or "")
    name = str(raw.get("nft_name") or raw.get("name") or raw.get("username") or addr)
    price = raw.get("price_per_day_rub") or raw.get("price_per_day") or raw.get("price_rub") or raw.get("price") or "0"
    data = {
        "kind": kind,
        "address": addr,
        "name": name,
        "price_per_day": str(money(price)),
        "buy_price": str(money(raw.get("buy_price") or raw.get("price_rub") or 0)),
        "min_days": int(raw.get("min_days") or 1),
        "max_days": int(raw.get("max_days") or 90),
        "available": bool(raw.get("available", True)),
        "collection": raw.get("collection") or raw.get("collection_address"),
        "collection_name": raw.get("collection_name")
        or ((raw.get("collection") or {}).get("name") if isinstance(raw.get("collection"), dict) else None),
        "tone": raw.get("tone") or (sum(ord(c) for c in name) % 360),
        "motif": _motif_of(name, raw.get("motif")),
        "model": raw.get("model"),
        "symbol": raw.get("symbol"),
        "source": raw.get("source") or "demo",
        "length": raw.get("length"),
        "digits": raw.get("digits"),
    }
    if extra:
        data.update(extra)
    return data


class Marketplace:
    def __init__(self, client: TgStarsClient | None = None):
        self.client = client or TgStarsClient()

    def _live(self) -> bool:
        s = get_settings()
        return bool(s.tgstars_api_key) and not s.demo_mode

    def nft_collections(self) -> dict:
        if self._live():
            try:
                raw = self.client.rent_nft_collections()
                cols = raw.get("collections") or []
                return {"items": cols, "total": raw.get("total", len(cols)), "source": "tgstars"}
            except TgStarsError:
                pass
        return {"items": DEMO_COLLECTIONS, "total": len(DEMO_COLLECTIONS), "source": "demo"}

    def nft_list(
        self,
        collection_address: str | None = None,
        search: str | None = None,
        *,
        sort_by: str | None = None,
        model: str | None = None,
        symbol: str | None = None,
        backdrop: str | None = None,
        cursor: str | None = None,
    ) -> dict:
        if self._live() and collection_address:
            try:
                raw = self.client.rent_nft_list(
                    collection_address,
                    sort_by=sort_by,
                    model=model,
                    symbol=symbol,
                    backdrop=backdrop,
                    cursor=cursor,
                )
                items = [_item("nft_rent", x, {"source": "tgstars"}) for x in (raw.get("items") or raw.get("nfts") or [])]
                return {"items": items, "total": raw.get("total", len(items)), "cursor": raw.get("cursor"), "source": "tgstars"}
            except TgStarsError:
                pass
        items = [_item("nft_rent", x) for x in DEMO_NFTS]
        if collection_address:
            items = [i for i in items if i.get("collection") == collection_address]
        if search:
            q = search.lower()
            items = [i for i in items if q in i["name"].lower()]
        if model:
            items = [i for i in items if (i.get("model") or "").lower() == model.lower()]
        if symbol:
            items = [i for i in items if (i.get("symbol") or "").lower() == symbol.lower()]
        if sort_by == "price_per_day":
            items = sorted(items, key=lambda i: float(i["price_per_day"]))
        return {"items": items, "total": len(items), "source": "demo"}

    def username_list(
        self,
        search: str | None = None,
        *,
        length_filter: list[int] | None = None,
        numbers_filter: str | None = None,
        underscore_filter: str | None = None,
        cursor: str | None = None,
        sort_by: str | None = None,
    ) -> dict:
        if self._live():
            try:
                raw = self.client.rent_username_list(
                    search=search,
                    length_filter=length_filter,
                    numbers_filter=numbers_filter,
                    underscore_filter=underscore_filter,
                    cursor=cursor,
                    sort_by=sort_by,
                )
                items = [_item("username_rent", x, {"source": "tgstars"}) for x in (raw.get("items") or [])]
                return {"items": items, "total": raw.get("total", len(items)), "cursor": raw.get("cursor"), "source": "tgstars"}
            except TgStarsError:
                pass
        items = [_item("username_rent", x) for x in DEMO_USERNAMES]
        if search:
            q = search.lower()
            items = [i for i in items if q in i["name"].lower()]
        if length_filter:
            lengths = {int(x) for x in length_filter}
            items = [i for i in items if int(i.get("length") or 0) in lengths]
        if numbers_filter == "with":
            items = [i for i in items if any(c.isdigit() for c in i["name"])]
        elif numbers_filter == "without":
            items = [i for i in items if not any(c.isdigit() for c in i["name"])]
        if underscore_filter == "with":
            items = [i for i in items if "_" in i["name"]]
        elif underscore_filter == "without":
            items = [i for i in items if "_" not in i["name"]]
        return {"items": items, "total": len(items), "source": "demo"}

    def number_list(self, *, length: str | None = None, sort_by: str | None = None, cursor: str | None = None) -> dict:
        if self._live():
            try:
                raw = self.client.rent_number_list(length=length, sort_by=sort_by, cursor=cursor)
                items = [_item("number_rent", x, {"source": "tgstars"}) for x in (raw.get("items") or [])]
                return {"items": items, "total": raw.get("total", len(items)), "cursor": raw.get("cursor"), "source": "tgstars"}
            except TgStarsError:
                pass
        items = [_item("number_rent", x) for x in DEMO_NUMBERS]
        if length == "short":
            items = [i for i in items if len(i.get("digits") or "") <= 4]
        elif length == "long":
            items = [i for i in items if len(i.get("digits") or "") > 4]
        if sort_by == "price_per_day":
            items = sorted(items, key=lambda i: float(i["price_per_day"]))
        return {"items": items, "total": len(items), "source": "demo"}

    def nft_buy_collections(self) -> dict:
        if self._live():
            try:
                raw = self.client.nft_buy_collections()
                return {"items": raw.get("collections") or [], "total": raw.get("total", 0), "source": "tgstars"}
            except TgStarsError:
                pass
        return {"items": DEMO_COLLECTIONS, "total": len(DEMO_COLLECTIONS), "source": "demo"}

    def nft_buy_list(
        self,
        collection_address: str | None = None,
        *,
        sort_order: str | None = None,
        model: str | None = None,
        symbol: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        cursor: str | None = None,
    ) -> dict:
        if self._live():
            try:
                raw = self.client.nft_buy_list(
                    collection_address=collection_address,
                    sort_order=sort_order,
                    model=model,
                    symbol=symbol,
                    min_price=min_price,
                    max_price=max_price,
                    cursor=cursor,
                )
                items = [_item("nft_buy", x, {"source": "tgstars"}) for x in (raw.get("nfts") or raw.get("items") or [])]
                return {"items": items, "total": raw.get("total", len(items)), "cursor": raw.get("cursor"), "source": "tgstars"}
            except TgStarsError:
                pass
        items = [_item("nft_buy", x) for x in DEMO_NFTS]
        if collection_address:
            items = [i for i in items if i.get("collection") == collection_address]
        if model:
            items = [i for i in items if (i.get("model") or "").lower() == model.lower()]
        if symbol:
            items = [i for i in items if (i.get("symbol") or "").lower() == symbol.lower()]
        if min_price is not None:
            items = [i for i in items if float(i["buy_price"]) >= float(min_price)]
        if max_price is not None:
            items = [i for i in items if float(i["buy_price"]) <= float(max_price)]
        if sort_order == "desc":
            items = sorted(items, key=lambda i: float(i["buy_price"]), reverse=True)
        elif sort_order == "asc":
            items = sorted(items, key=lambda i: float(i["buy_price"]))
        return {"items": items, "total": len(items), "source": "demo"}

    def nft_buy_info(self, address: str) -> dict | None:
        if self._live():
            try:
                raw = self.client.nft_buy_info(address)
                nft = raw.get("nft") or raw
                return _item(
                    "nft_buy",
                    {
                        "address": nft.get("address") or address,
                        "name": nft.get("name") or address,
                        "buy_price": nft.get("price_rub") or 0,
                        "available": nft.get("available_for_buy", True),
                        "collection": nft.get("collection"),
                    },
                    {"source": "tgstars", "attributes": nft.get("attributes") or [], "available": bool(nft.get("available_for_buy", True))},
                )
            except TgStarsError:
                pass
        return self.get_asset("nft_buy", address)

    def get_asset(self, kind: str, address: str) -> dict | None:
        pools = {
            "nft_rent": self.nft_list().get("items") or [],
            "nft_buy": self.nft_buy_list().get("items") or [],
            "username_rent": self.username_list().get("items") or [],
            "number_rent": self.number_list().get("items") or [],
        }
        for item in pools.get(kind, []):
            if item["address"] == address or item["name"] == address:
                return item
        return None

    def quote(self, kind: str, address: str, days: int = 1) -> dict:
        settings = get_settings()
        asset = self.get_asset(kind, address)
        live_fn = {
            "nft_rent": self.client.get_nft_rent_rate,
            "username_rent": self.client.get_username_rent_rate,
            "number_rent": self.client.get_number_rent_rate,
        }.get(kind)
        if live_fn and settings.tgstars_api_key and not settings.demo_mode:
            try:
                raw = live_fn(address, days)
                per = money(raw.get("price_per_day_rub") or 0)
                qty = int(raw.get("days") or days)
                return {
                    "kind": kind,
                    "address": address,
                    "name": raw.get("nft_name") or (asset or {}).get("name") or address,
                    "available": bool(raw.get("available", True)),
                    "unit_price": per,
                    "quantity": qty,
                    "min_quantity": int(raw.get("min_days") or 1),
                    "max_quantity": int(raw.get("max_days") or 90),
                    "total": money(raw.get("total_rub") or per * qty),
                    "source": "tgstars",
                    "tone": (asset or {}).get("tone"),
                    "motif": (asset or {}).get("motif") or _motif_of(raw.get("nft_name") or address),
                }
            except TgStarsError:
                pass
        if kind == "nft_buy":
            info = self.nft_buy_info(address) or asset or {}
            price = money(info.get("buy_price") or 0)
            return {
                "kind": kind,
                "address": address,
                "name": info.get("name") or address,
                "available": bool(info.get("available", True)),
                "unit_price": price,
                "quantity": 1,
                "min_quantity": 1,
                "max_quantity": 1,
                "total": price,
                "source": info.get("source") or "demo",
                "tone": info.get("tone"),
                "motif": info.get("motif") or _motif_of(info.get("name") or address),
            }
        if not asset:
            return {
                "kind": kind,
                "address": address,
                "name": address,
                "available": False,
                "unit_price": money(0),
                "quantity": days,
                "min_quantity": 1,
                "max_quantity": 90,
                "total": money(0),
                "source": "demo",
                "motif": "gift",
            }
        qty = max(int(asset["min_days"]), min(int(days), int(asset["max_days"])))
        unit = money(asset["price_per_day"])
        return {
            "kind": kind,
            "address": address,
            "name": asset["name"],
            "available": True,
            "unit_price": unit,
            "quantity": qty,
            "min_quantity": int(asset["min_days"]),
            "max_quantity": int(asset["max_days"]),
            "total": money(unit * qty),
            "source": asset.get("source") or "demo",
            "tone": asset.get("tone"),
            "motif": asset.get("motif") or _motif_of(asset["name"]),
        }
