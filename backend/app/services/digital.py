from __future__ import annotations

import secrets
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, InsufficientBalance, NotFoundError
from app.core.money import apply_markup, money
from app.models import DigitalCode, DigitalOrder, DigitalProduct, Transaction, User
from app.models.entities import utcnow
from app.services.audit import write_audit
from app.services.codes import decrypt_code, encrypt_code, hash_code, mask_code
from app.services.notify import notify_owner, send_telegram
from app.services.orders import _lock_balance

CATEGORIES = {
    "steam": "Steam",
    "google_play": "Google Play",
    "app_store": "App Store",
    "playstation": "PlayStation",
    "xbox": "Xbox",
    "nintendo": "Nintendo",
    "roblox": "Roblox",
    "minecraft": "Minecraft",
    "fortnite": "Fortnite",
    "valorant": "Valorant",
    "spotify": "Spotify",
    "other": "Другое",
}
GROUPS = {"topup": "Пополнения", "games": "Игры"}


def _public_id() -> str:
    return "DG" + "".join(str(secrets.randbelow(10)) for _ in range(6))


def stock_of(db: Session, product_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(DigitalCode)
            .where(DigitalCode.product_id == product_id, DigitalCode.status == "available")
        )
        or 0
    )


def product_public(db: Session, p: DigitalProduct, *, stock: int | None = None) -> dict:
    qty = stock if stock is not None else stock_of(db, p.id)
    custom = (p.amount_mode or "fixed") == "custom"
    return {
        "id": p.id,
        "slug": p.slug,
        "name": p.name,
        "description": p.description,
        "category": p.category,
        "category_label": CATEGORIES.get(p.category, p.category),
        "group": p.group,
        "provider": p.provider,
        "image": p.image or None,
        "region": p.region,
        "currency": p.currency,
        "face_value": p.face_value,
        "price": f"{money(p.price):.2f}",
        "amount_mode": p.amount_mode or "fixed",
        "markup_percent": f"{money(p.markup_percent):.2f}",
        "min_amount": f"{money(p.min_amount):.2f}",
        "max_amount": f"{money(p.max_amount):.2f}",
        "delivery_type": p.delivery_type,
        "extra_fields": p.extra_fields or [],
        "enabled": p.enabled,
        "stock": qty,
        "in_stock": custom or qty > 0 or p.delivery_type == "manual",
    }


def order_public(order: DigitalOrder, *, reveal: bool = False) -> dict:
    product = order.product
    code = None
    if reveal and order.result and order.user_id:
        code = (order.result or {}).get("code")
    return {
        "id": order.id,
        "public_id": order.public_id,
        "product_id": order.product_id,
        "product_name": product.name if product else "",
        "category": product.category if product else "",
        "region": product.region if product else "",
        "face_value": product.face_value if product else "",
        "price": f"{money(order.price):.2f}",
        "status": order.status,
        "extra": order.extra or {},
        "code": code,
        "delivery_type": product.delivery_type if product else "code",
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def list_products(db: Session, *, group: str | None = None, category: str | None = None, only_enabled: bool = True):
    stmt = select(DigitalProduct)
    if only_enabled:
        stmt = stmt.where(DigitalProduct.enabled.is_(True))
    if group:
        stmt = stmt.where(DigitalProduct.group == group)
    if category and category != "all":
        stmt = stmt.where(DigitalProduct.category == category)
    return list(db.scalars(stmt.order_by(DigitalProduct.sort_order, DigitalProduct.id)))


def add_codes(db: Session, product: DigitalProduct, lines: list[str], actor_id: int | None) -> dict:
    added = 0
    skipped = 0
    seen: set[str] = set()
    for raw in lines:
        plain = (raw or "").strip()
        if not plain:
            continue
        digest = hash_code(plain)
        if digest in seen:
            skipped += 1
            continue
        seen.add(digest)
        exists = db.scalar(
            select(DigitalCode.id).where(DigitalCode.product_id == product.id, DigitalCode.code_hash == digest)
        )
        if exists:
            skipped += 1
            continue
        db.add(
            DigitalCode(
                product_id=product.id,
                code_enc=encrypt_code(plain),
                code_hash=digest,
                status="available",
            )
        )
        added += 1
    write_audit(db, "digital.codes.add", actor_id, "digital_product", product.id, {"added": added, "skipped": skipped})
    db.commit()
    return {"added": added, "skipped": skipped, "stock": stock_of(db, product.id)}


def _take_code(db: Session, product_id: int) -> DigitalCode | None:
    stmt = select(DigitalCode).where(DigitalCode.product_id == product_id, DigitalCode.status == "available")
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    else:
        stmt = stmt.with_for_update()
    return db.scalars(stmt.limit(1)).first()


def _collect_extra(product: DigitalProduct, extra: dict | None) -> tuple:
    payload: dict = {}
    fields = product.extra_fields or []
    for field in fields:
        name = field.get("key")
        if not name or name == "amount":
            continue
        value = str((extra or {}).get(name) or "").strip()
        if field.get("required") and not value:
            raise AppError("MISSING_FIELD", f"Укажите {field.get('label') or name}")
        if value:
            payload[name] = value[:64]

    custom = (product.amount_mode or "fixed") == "custom"
    if custom:
        raw = (extra or {}).get("amount")
        try:
            face = money(raw)
        except Exception:
            face = money(0)
        if face <= 0:
            raise AppError("INVALID_AMOUNT", "Укажите сумму пополнения")
        min_a = money(product.min_amount)
        max_a = money(product.max_amount)
        if min_a > 0 and face < min_a:
            raise AppError("INVALID_AMOUNT", f"Минимум {min_a:.0f} ₽")
        if max_a > 0 and face > max_a:
            raise AppError("INVALID_AMOUNT", f"Максимум {max_a:.0f} ₽")
        price = apply_markup(face, product.markup_percent or 0)
        payload["amount"] = f"{face:.2f}"
        return price, payload

    price = money(product.price)
    if price <= 0:
        raise AppError("INVALID_PRICE", "У товара не задана цена")
    return price, payload


def purchase(
    db: Session,
    *,
    user: User,
    product_id: int,
    extra: dict | None,
    idempotency_key: str,
) -> DigitalOrder:
    key = (idempotency_key or "").strip()[:80]
    if not key:
        raise AppError("IDEMPOTENCY_REQUIRED", "Нужен ключ идемпотентности")
    existing = db.scalar(
        select(DigitalOrder)
        .options(selectinload(DigitalOrder.product))
        .where(DigitalOrder.user_id == user.id, DigitalOrder.idempotency_key == key)
    )
    if existing:
        return existing

    product = db.get(DigitalProduct, product_id)
    if not product or not product.enabled:
        raise NotFoundError("Товар не найден")
    price, payload = _collect_extra(product, extra)

    if product.delivery_type == "code" and (product.amount_mode or "fixed") != "custom" and stock_of(db, product.id) < 1:
        raise AppError("OUT_OF_STOCK", "Кодов нет в наличии")

    bal = _lock_balance(db, user.id)
    before = money(bal.amount)
    if before < price:
        raise InsufficientBalance("Недостаточно средств")
    after = money(before - price)
    bal.amount = after

    oid = _public_id()
    while db.scalar(select(DigitalOrder.id).where(DigitalOrder.public_id == oid)):
        oid = _public_id()
    order = DigitalOrder(
        public_id=oid,
        user_id=user.id,
        product_id=product.id,
        price=price,
        status="pending",
        extra=payload or None,
        idempotency_key=key,
    )
    db.add(order)
    db.flush()
    db.add(
        Transaction(
            user_id=user.id,
            type="DIGITAL",
            amount=money(-price),
            balance_before=before,
            balance_after=after,
            description=f"Digital · {product.name} · {oid}",
            payload={"digital_order": oid, "product_id": product.id},
        )
    )
    try:
        _deliver(db, order, product)
    except AppError:
        bal.amount = before
        order.status = "failed"
        db.add(
            Transaction(
                user_id=user.id,
                type="REFUND",
                amount=price,
                balance_before=after,
                balance_after=before,
                description=f"Возврат · {oid}",
                payload={"digital_order": oid},
            )
        )
        write_audit(db, "digital.fail", user.id, "digital_order", oid)
        db.commit()
        db.refresh(order)
        raise
    write_audit(db, "digital.purchase", user.id, "digital_order", oid, {"price": str(price)})
    db.commit()
    db.refresh(order)
    if order.status == "completed" and order.result and order.result.get("code"):
        send_telegram(user, f"Покупка {product.name}\nЗаказ {oid}\nВаш код выдан в разделе «Мои покупки».")
    elif order.status == "processing":
        login = (payload or {}).get("steam_login") or (payload or {}).get("username") or ""
        face = (payload or {}).get("amount") or product.face_value
        send_telegram(user, f"Заказ {oid} принят.\n{product.name}" + (f"\nАккаунт: {login}" if login else "") + (f"\nСумма: {face}" if face else "") + "\nПриз/пополнение будет выдано после обработки.")
        notify_owner(db, f"Digital заказ {oid}: {product.name}\nЦена {price:.2f} ₽\n{payload}")
    return order


def _deliver(db: Session, order: DigitalOrder, product: DigitalProduct) -> None:
    if product.delivery_type == "manual":
        order.status = "processing"
        return
    code = _take_code(db, product.id)
    if not code:
        order.status = "processing"
        raise AppError("OUT_OF_STOCK", "Кодов нет в наличии")
    plain = decrypt_code(code.code_enc)
    if not plain:
        code.status = "disabled"
        raise AppError("CODE_CORRUPT", "Код повреждён, средства вернутся")
    now = utcnow()
    code.status = "sold"
    code.order_id = order.id
    code.reserved_at = now
    code.sold_at = now
    order.code_id = code.id
    order.result = {"code": plain, "masked": mask_code(plain)}
    order.status = "completed"


def fulfill_manual(db: Session, order: DigitalOrder, code_plain: str, actor: User) -> DigitalOrder:
    if order.status == "completed":
        return order
    if order.status not in {"pending", "processing"}:
        raise AppError("INVALID_STATUS", "Этот заказ нельзя выдать")
    plain = (code_plain or "").strip()
    if not plain:
        raise AppError("MISSING_CODE", "Укажите код")
    order.result = {"code": plain, "masked": mask_code(plain)}
    order.status = "completed"
    write_audit(db, "digital.fulfill", actor.id, "digital_order", order.public_id)
    db.commit()
    db.refresh(order)
    user = db.get(User, order.user_id)
    send_telegram(user, f"Ваш приз/заказ {order.public_id} выдан. Откройте «Мои покупки».")
    return order


def grant_product(db: Session, user: User, product: DigitalProduct, *, idempotency_key: str) -> DigitalOrder:
    key = (idempotency_key or "")[:80]
    existing = db.scalar(
        select(DigitalOrder)
        .options(selectinload(DigitalOrder.product))
        .where(DigitalOrder.user_id == user.id, DigitalOrder.idempotency_key == key)
    )
    if existing:
        return existing
    oid = _public_id()
    while db.scalar(select(DigitalOrder.id).where(DigitalOrder.public_id == oid)):
        oid = _public_id()
    order = DigitalOrder(
        public_id=oid,
        user_id=user.id,
        product_id=product.id,
        price=money(0),
        status="pending",
        extra={"source": "giveaway"},
        idempotency_key=key,
    )
    db.add(order)
    db.flush()
    try:
        _deliver(db, order, product)
    except AppError:
        order.status = "processing"
    return order
