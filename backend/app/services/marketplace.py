from __future__ import annotations

import logging
import time
from typing import Any

from app.core.config import get_settings
from app.core.money import money
from app.integrations.tgstars.client import TgStarsClient
from app.integrations.tgstars.exceptions import TgStarsError

log = logging.getLogger("MARKET")

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

_cache: dict[str, tuple[float, Any]] = {}
_index: dict[tuple[str, str], dict] = {}
CACHE_TTL = 55.0


def _remember(kind: str, items: list[dict]) -> list[dict]:
    for item in items:
        _index[(kind, item["address"])] = item
        _index[(kind, item["name"])] = item
    return items


def _cached(key: str, loader):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]
    data = loader()
    _cache[key] = (now, data)
    return data


def display_image(raw: dict | str | None, kind: str | None = None) -> str | None:
    if isinstance(raw, str):
        img = raw
        if img.endswith(".tgs"):
            img = img[:-4] + ".webp"
        return img or None
    if not isinstance(raw, dict):
        return None
    slug = str(raw.get("slug") or "").strip()
    if slug:
        folder = "username" if kind == "username_rent" else "number" if kind == "number_rent" else "gift"
        return f"https://nft.fragment.com/{folder}/{slug.lower()}.webp"
    img = str(raw.get("image") or raw.get("alternative_image") or raw.get("preview") or "")
    if not img:
        return None
    if img.endswith(".tgs"):
        base = img.rsplit("/", 1)[-1][:-4]
        clean = "".join(ch for ch in base if ch.isalnum() or ch in "-_").lower()
        return f"https://nft.fragment.com/gift/{clean}.webp"
    return img


def display_name(kind: str, raw: dict, address: str) -> str:
    name = str(raw.get("nft_name") or raw.get("name") or raw.get("username") or raw.get("number") or "")
    name = name.strip()
    if kind == "username_rent":
        name = name.lstrip("@")
    if not name or name.startswith("EQ") or name.lower().startswith("eq-"):
        if kind == "username_rent":
            return "username"
        if kind == "number_rent":
            return "номер"
        return "лот"
    return name


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
    name = display_name(kind, raw, addr)
    price = raw.get("price_per_day_rub") or raw.get("price_per_day") or raw.get("price_rub") or raw.get("price") or "0"
    image = display_image(raw, kind)
    handle = name.lstrip("@")
    digits = raw.get("digits") or "".join(ch for ch in name if ch.isdigit())
    data = {
        "kind": kind,
        "address": addr,
        "name": handle if kind == "username_rent" else name,
        "price_per_day": str(money(price)),
        "buy_price": str(money(raw.get("buy_price") or raw.get("price_rub") or 0)),
        "min_days": int(raw.get("min_days") or 1),
        "max_days": int(raw.get("max_days") or 90),
        "available": bool(raw.get("available", True)),
        "collection": raw.get("collection") or raw.get("collection_address"),
        "collection_name": raw.get("collection_name")
        or ((raw.get("collection") or {}).get("name") if isinstance(raw.get("collection"), dict) else None),
        "tone": raw.get("tone") or (sum(ord(c) for c in name) % 360 if name else 210),
        "motif": _motif_of(name, raw.get("motif")),
        "model": raw.get("model"),
        "symbol": raw.get("symbol"),
        "source": raw.get("source") or "demo",
        "length": raw.get("length") or (len(handle) if kind == "username_rent" else None),
        "digits": digits or None,
        "image": image,
    }
    if extra:
        data.update(extra)
    return data


class Marketplace:
    def __init__(self, client: TgStarsClient | None = None):
        self.client = client or TgStarsClient()

    def _can_read(self) -> bool:
        return bool(get_settings().tgstars_api_key)

    def _empty(self, source: str = "tgstars", error: str | None = None) -> dict:
        data: dict[str, Any] = {"items": [], "total": 0, "source": source}
        if error:
            data["error"] = error
        return data

    def nft_collections(self) -> dict:
        if self._can_read():
            try:
                return _cached("nft_collections", self._load_nft_collections)
            except TgStarsError as exc:
                log.warning("nft collections: %s", exc)
                return self._empty(error="Не удалось загрузить коллекции")
        return {"items": DEMO_COLLECTIONS, "total": len(DEMO_COLLECTIONS), "source": "demo"}

    def _load_nft_collections(self) -> dict:
        raw = self.client.rent_nft_collections()
        cols = []
        for c in raw.get("collections") or []:
            cols.append(
                {
                    "address": c.get("address"),
                    "name": c.get("name"),
                    "image": display_image(c),
                    "count": c.get("nft_items") or c.get("count") or 0,
                    "kind": "nft",
                    "floor_price": c.get("floor_price"),
                }
            )
        return {"items": cols, "total": raw.get("total", len(cols)), "source": "tgstars"}

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
        if self._can_read():
            try:
                addr = collection_address
                if not addr:
                    cols = self.nft_collections().get("items") or []
                    addr = (cols[0] or {}).get("address") if cols else None
                if not addr:
                    return self._empty(error="Нет доступных коллекций")
                key = f"nft_list:{addr}:{sort_by}:{model}:{symbol}:{backdrop}:{cursor}:{search}"
                return _cached(key, lambda: self._load_nft_list(addr, search, sort_by, model, symbol, backdrop, cursor))
            except TgStarsError as exc:
                log.warning("nft list: %s", exc)
                return self._empty(error="Не удалось загрузить NFT")
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

    def _load_nft_list(self, collection_address, search, sort_by, model, symbol, backdrop, cursor) -> dict:
        raw = self.client.rent_nft_list(
            collection_address,
            sort_by=sort_by,
            model=model,
            symbol=symbol,
            backdrop=backdrop,
            cursor=cursor,
        )
        items = [_item("nft_rent", x, {"source": "tgstars", "collection": collection_address}) for x in (raw.get("items") or raw.get("nfts") or [])]
        if search:
            q = search.lower()
            items = [i for i in items if q in i["name"].lower()]
        _remember("nft_rent", items)
        return {"items": items, "total": raw.get("total", len(items)), "cursor": raw.get("cursor"), "source": "tgstars"}

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
        if self._can_read():
            try:
                key = f"user_list:{search}:{length_filter}:{numbers_filter}:{underscore_filter}:{cursor}:{sort_by}"
                return _cached(
                    key,
                    lambda: self._load_usernames(search, length_filter, numbers_filter, underscore_filter, cursor, sort_by),
                )
            except TgStarsError as exc:
                log.warning("username list: %s", exc)
                return self._empty(error="Не удалось загрузить username")
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

    def _load_usernames(self, search, length_filter, numbers_filter, underscore_filter, cursor, sort_by) -> dict:
        raw = self.client.rent_username_list(
            search=search,
            length_filter=length_filter,
            numbers_filter=numbers_filter,
            underscore_filter=underscore_filter,
            cursor=cursor,
            sort_by=sort_by,
        )
        items = [_item("username_rent", x, {"source": "tgstars"}) for x in (raw.get("items") or [])]
        _remember("username_rent", items)
        return {"items": items, "total": raw.get("total", len(items)), "cursor": raw.get("cursor"), "source": "tgstars"}

    def number_list(self, *, length: str | None = None, sort_by: str | None = None, cursor: str | None = None) -> dict:
        if self._can_read():
            try:
                key = f"num_list:{length}:{sort_by}:{cursor}"
                return _cached(key, lambda: self._load_numbers(length, sort_by, cursor))
            except TgStarsError as exc:
                log.warning("number list: %s", exc)
                return self._empty(error="Не удалось загрузить номера")
        items = [_item("number_rent", x) for x in DEMO_NUMBERS]
        if length == "short":
            items = [i for i in items if len(i.get("digits") or "") <= 4]
        elif length == "long":
            items = [i for i in items if len(i.get("digits") or "") > 4]
        if sort_by == "price_per_day":
            items = sorted(items, key=lambda i: float(i["price_per_day"]))
        return {"items": items, "total": len(items), "source": "demo"}

    def _load_numbers(self, length, sort_by, cursor) -> dict:
        raw = self.client.rent_number_list(length=length, sort_by=sort_by, cursor=cursor)
        items = [_item("number_rent", x, {"source": "tgstars"}) for x in (raw.get("items") or [])]
        _remember("number_rent", items)
        return {"items": items, "total": raw.get("total", len(items)), "cursor": raw.get("cursor"), "source": "tgstars"}

    def nft_buy_collections(self) -> dict:
        if self._can_read():
            try:
                return _cached("nft_buy_collections", self._load_buy_collections)
            except TgStarsError as exc:
                log.warning("nft buy collections: %s", exc)
                return self._empty(error="Не удалось загрузить коллекции")
        return {"items": DEMO_COLLECTIONS, "total": len(DEMO_COLLECTIONS), "source": "demo"}

    def _load_buy_collections(self) -> dict:
        raw = self.client.nft_buy_collections()
        cols = []
        for c in raw.get("collections") or []:
            cols.append(
                {
                    "address": c.get("address"),
                    "name": c.get("name"),
                    "image": display_image(c),
                    "count": c.get("nft_items") or c.get("count") or 0,
                }
            )
        return {"items": cols, "total": raw.get("total", len(cols)), "source": "tgstars"}

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
        if self._can_read():
            try:
                addr = collection_address
                if not addr:
                    cols = self.nft_buy_collections().get("items") or []
                    addr = (cols[0] or {}).get("address") if cols else None
                if not addr:
                    return self._empty(error="Нет доступных коллекций")
                key = f"nft_buy:{addr}:{sort_order}:{model}:{symbol}:{min_price}:{max_price}:{cursor}"
                return _cached(key, lambda: self._load_buy_list(addr, sort_order, model, symbol, min_price, max_price, cursor))
            except TgStarsError as exc:
                log.warning("nft buy list: %s", exc)
                return self._empty(error="Не удалось загрузить NFT")
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

    def _load_buy_list(self, collection_address, sort_order, model, symbol, min_price, max_price, cursor) -> dict:
        raw = self.client.nft_buy_list(
            collection_address=collection_address,
            sort_order=sort_order,
            model=model,
            symbol=symbol,
            min_price=min_price,
            max_price=max_price,
            cursor=cursor,
        )
        items = [_item("nft_buy", x, {"source": "tgstars", "collection": collection_address}) for x in (raw.get("nfts") or raw.get("items") or [])]
        _remember("nft_buy", items)
        return {"items": items, "total": raw.get("total", len(items)), "cursor": raw.get("cursor"), "source": "tgstars"}

    def nft_buy_info(self, address: str) -> dict | None:
        if self._can_read():
            try:
                raw = self.client.nft_buy_info(address)
                nft = raw.get("nft") or raw
                return _item(
                    "nft_buy",
                    {
                        "address": nft.get("address") or nft.get("nft_address") or address,
                        "name": nft.get("name") or address,
                        "image": nft.get("image"),
                        "buy_price": nft.get("price_rub") or 0,
                        "available": nft.get("available_for_buy", True),
                        "collection": nft.get("collection"),
                    },
                    {"source": "tgstars", "attributes": nft.get("attributes") or [], "available": bool(nft.get("available_for_buy", True))},
                )
            except TgStarsError as exc:
                log.warning("nft buy info: %s", exc)
        return self.get_asset("nft_buy", address)

    def get_asset(self, kind: str, address: str) -> dict | None:
        needle = (address or "").lstrip("@")
        hit = _index.get((kind, address)) or _index.get((kind, needle))
        if hit:
            return hit
        if kind == "nft_rent":
            pool = self.nft_list().get("items") or []
        elif kind == "nft_buy":
            pool = self.nft_buy_list().get("items") or []
        elif kind == "username_rent":
            pool = self.username_list().get("items") or []
        elif kind == "number_rent":
            pool = self.number_list().get("items") or []
        else:
            pool = []
        needle = (address or "").lstrip("@")
        for item in pool:
            if item["address"] == address or item["name"] == needle or item["name"].lstrip("@") == needle:
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
        if kind == "nft_buy":
            info = asset or self.nft_buy_info(address) or {}
            price = money(info.get("buy_price") or 0)
            name = info.get("name") or address
            return {
                "kind": kind,
                "address": address,
                "name": name if not str(name).startswith("EQ") else "Подарок",
                "available": bool(info.get("available", True)),
                "unit_price": price,
                "quantity": 1,
                "min_quantity": 1,
                "max_quantity": 1,
                "total": price,
                "source": info.get("source") or "demo",
                "tone": info.get("tone"),
                "motif": info.get("motif") or _motif_of(str(name)),
                "image": info.get("image"),
            }
        if asset:
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
                "image": asset.get("image"),
            }
        if live_fn and settings.tgstars_api_key:
            try:
                raw = live_fn(address, days)
                per = money(raw.get("price_per_day_rub") or 0)
                qty = int(raw.get("days") or days)
                name = display_name(kind, raw, address)
                return {
                    "kind": kind,
                    "address": address,
                    "name": name,
                    "available": bool(raw.get("available", True)),
                    "unit_price": per,
                    "quantity": qty,
                    "min_quantity": int(raw.get("min_days") or 1),
                    "max_quantity": int(raw.get("max_days") or 90),
                    "total": money(raw.get("total_rub") or per * qty),
                    "source": "tgstars",
                    "tone": None,
                    "motif": _motif_of(name),
                    "image": display_image(raw),
                }
            except TgStarsError as exc:
                log.warning("quote live failed: %s", exc)
        return {
            "kind": kind,
            "address": address,
            "name": "Лот",
            "available": False,
            "unit_price": money(0),
            "quantity": days,
            "min_quantity": 1,
            "max_quantity": 90,
            "total": money(0),
            "source": "demo",
            "motif": "gift",
            "image": None,
        }
