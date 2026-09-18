from __future__ import annotations

import secrets
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import AppError, InsufficientBalance, NotFoundError
from app.core.money import money, percent_of
from app.integrations.tgstars.service import TgStarsService
from app.models import (
    Balance,
    IdempotencyKey,
    Mirror,
    MirrorTransaction,
    Order,
    Product,
    Referral,
    ReferralReward,
    Transaction,
    User,
)
from app.services.audit import write_audit
from app.services.catalog import load_mirror, quote_product
from app.services.processors import get_processor


def _public_id() -> str:
    return "A" + "".join(str(secrets.randbelow(10)) for _ in range(6))


def _lock_balance(db: Session, user_id: int) -> Balance:
    stmt = select(Balance).where(Balance.user_id == user_id)
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    bal = db.scalar(stmt)
    if bal is None:
        bal = Balance(user_id=user_id, amount=Decimal("0.00"))
        db.add(bal)
        db.flush()
        if db.get_bind().dialect.name == "postgresql":
            bal = db.scalar(select(Balance).where(Balance.user_id == user_id).with_for_update())
    return bal


def checkout(
    db: Session,
    *,
    user: User,
    product_id: int,
    quantity: int,
    recipient: str,
    idempotency_key: str,
    tgstars: TgStarsService | None = None,
) -> Order:
    settings = get_settings()
    tgstars = tgstars or TgStarsService()
    key = (idempotency_key or "").strip()[:80]
    if not key:
        raise AppError("IDEMPOTENCY_REQUIRED", "Нужен ключ идемпотентности")

    existing = db.scalar(select(IdempotencyKey).where(IdempotencyKey.user_id == user.id, IdempotencyKey.key == key))
    if existing and existing.order_id:
        order = db.scalar(select(Order).options(selectinload(Order.product)).where(Order.id == existing.order_id))
        if order:
            return order

    product = db.get(Product, product_id)
    if not product or not product.enabled:
        raise NotFoundError("Товар не найден")

    qty = int(quantity)
    if qty < product.min_quantity or qty > product.max_quantity:
        raise AppError("INVALID_QUANTITY", "Некорректное количество")

    dest = (recipient or user.username or "").lstrip("@").strip()
    if len(dest) < 3:
        raise AppError("INVALID_RECIPIENT", "Укажите Telegram username получателя")

    check_type = "premium" if product.kind == "premium" else "stars"
    months = qty if product.kind == "premium" else None
    checked = tgstars.check_username(dest, type=check_type, months=months)
    if checked.get("valid") is False:
        raise AppError("INVALID_RECIPIENT", "Получатель не может принять этот товар")

    mirror = load_mirror(db, user.mirror_id)
    quote = quote_product(db, product, qty, mirror, tgstars)
    total = money(quote["total"])

    bal = _lock_balance(db, user.id)
    if money(bal.amount) < total:
        raise InsufficientBalance("Недостаточно средств")

    before = money(bal.amount)
    after = money(before - total)
    bal.amount = after

    order = Order(
        public_id=_public_id(),
        user_id=user.id,
        mirror_id=user.mirror_id,
        product_id=product.id,
        provider="tgstars",
        quantity=quote["quantity"],
        unit_price=quote["unit_price"],
        total_price=total,
        provider_cost=quote["provider_cost"],
        markup_amount=quote["markup_amount"],
        commission_amount=quote["commission_amount"],
        profit=quote["profit"],
        currency="RUB",
        status="PENDING",
        recipient=dest,
        payload={"quote_source": quote["source"]},
    )
    db.add(order)
    db.flush()

    db.add(
        Transaction(
            user_id=user.id,
            type="PURCHASE",
            amount=money(-total),
            balance_before=before,
            balance_after=after,
            description=f"Покупка {product.name} × {quote['quantity']}",
            payload={"order_id": order.id, "public_id": order.public_id},
        )
    )

    if existing:
        existing.order_id = order.id
    else:
        db.add(IdempotencyKey(user_id=user.id, key=key, order_id=order.id))

    processor = get_processor()
    processor.process(db, order)

    if settings.referral_enabled and user.referred_by and order.status in {"APPROVED", "COMPLETED", "PROCESSING"}:
        _pay_referral(db, user, order, settings.referral_percent, mirror)

    if mirror:
        db.add(
            MirrorTransaction(
                mirror_id=mirror.id,
                order_id=order.id,
                gross_amount=total,
                provider_cost=quote["provider_cost"],
                markup=quote["markup_amount"],
                commission=quote["commission_amount"],
                profit=quote["profit"],
            )
        )

    write_audit(
        db,
        "order.create",
        actor_id=user.id,
        entity="order",
        entity_id=order.public_id,
        payload={"status": order.status, "total": str(total)},
    )
    db.commit()
    db.refresh(order)
    order.product = product
    return order


def _pay_referral(db: Session, user: User, order: Order, percent, mirror: Mirror | None):
    pct = mirror.referral_percent if mirror and mirror.referral_percent is not None else percent
    amount = percent_of(order.total_price, pct)
    if amount <= 0:
        return
    owner_id = user.referred_by
    if not owner_id:
        return
    referral = db.scalar(select(Referral).where(Referral.invited_user_id == user.id))
    if not referral:
        return
    owner_bal = _lock_balance(db, owner_id)
    before = money(owner_bal.amount)
    after = money(before + amount)
    owner_bal.amount = after
    db.add(
        Transaction(
            user_id=owner_id,
            type="REFERRAL_REWARD",
            amount=amount,
            balance_before=before,
            balance_after=after,
            description=f"Реферальное вознаграждение с заказа #{order.public_id}",
            payload={"order_id": order.id},
        )
    )
    db.add(ReferralReward(referral_id=referral.id, order_id=order.id, amount=amount, status="COMPLETED"))


def refund_order(db: Session, order: Order, actor: User) -> Order:
    if order.status in {"REFUNDED", "CANCELLED"}:
        raise AppError("INVALID_STATUS", "Заказ уже возвращён")
    if order.status not in {"APPROVED", "COMPLETED", "PROCESSING", "FAILED"}:
        raise AppError("INVALID_STATUS", "Этот заказ нельзя вернуть")
    bal = _lock_balance(db, order.user_id)
    before = money(bal.amount)
    after = money(before + money(order.total_price))
    bal.amount = after
    db.add(
        Transaction(
            user_id=order.user_id,
            type="REFUND",
            amount=money(order.total_price),
            balance_before=before,
            balance_after=after,
            description=f"Возврат по заказу #{order.public_id}",
            payload={"order_id": order.id},
        )
    )
    order.status = "REFUNDED"
    write_audit(db, "order.refund", actor_id=actor.id, entity="order", entity_id=order.public_id)
    db.commit()
    db.refresh(order)
    return order
