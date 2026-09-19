from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, NotFoundError
from app.core.money import money, percent_of
from app.models import Product, PromoCode, PromoRedemption, Transaction, User

CODE_RE = re.compile(r"^[A-Z0-9]{3,32}$")


def normalize_code(raw: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (raw or "").upper())


def generate_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "LUM" + "".join(secrets.choice(alphabet) for _ in range(6))


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _now() -> datetime:
    return datetime.now(timezone.utc)


def promo_public(promo: PromoCode) -> dict:
    product = getattr(promo, "product", None)
    return {
        "id": promo.id,
        "code": promo.code,
        "kind": promo.kind,
        "amount_type": promo.amount_type,
        "amount": f"{money(promo.amount):.2f}",
        "product_id": promo.product_id,
        "product_name": product.name if product else None,
        "max_uses": promo.max_uses,
        "per_user": promo.per_user,
        "min_order": f"{money(promo.min_order):.2f}",
        "uses_count": promo.uses_count,
        "enabled": promo.enabled,
        "starts_at": promo.starts_at.isoformat() if promo.starts_at else None,
        "expires_at": promo.expires_at.isoformat() if promo.expires_at else None,
        "note": promo.note or "",
        "created_at": promo.created_at.isoformat() if promo.created_at else None,
    }


def validate_payload(*, kind: str, amount_type: str, amount, product_id: int | None) -> None:
    if kind not in {"balance", "discount", "product"}:
        raise AppError("INVALID_PROMO", "Тип промокода: баланс, скидка или товар")
    if amount_type not in {"fixed", "percent"}:
        raise AppError("INVALID_PROMO", "Сумма: фиксированная или проценты")
    value = money(amount)
    if value <= 0:
        raise AppError("INVALID_PROMO", "Укажите значение больше нуля")
    if amount_type == "percent" and value > 100:
        raise AppError("INVALID_PROMO", "Процент не больше 100")
    if kind == "balance" and amount_type != "fixed":
        raise AppError("INVALID_PROMO", "Баланс начисляется фиксированной суммой")
    if kind == "product" and not product_id:
        raise AppError("INVALID_PROMO", "Для товарного промокода выберите товар")


def _lock_promo(db: Session, code: str) -> PromoCode:
    stmt = select(PromoCode).options(selectinload(PromoCode.product)).where(PromoCode.code == code)
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    promo = db.scalar(stmt)
    if not promo:
        raise NotFoundError("Промокод не найден")
    return promo


def assert_redeemable(db: Session, promo: PromoCode, user: User, *, product: Product | None = None, total: Decimal | None = None) -> None:
    now = _now()
    if not promo.enabled:
        raise AppError("PROMO_INACTIVE", "Промокод отключён")
    starts = _aware(promo.starts_at)
    expires = _aware(promo.expires_at)
    if starts and now < starts:
        raise AppError("PROMO_INACTIVE", "Промокод ещё не действует")
    if expires and now > expires:
        raise AppError("PROMO_EXPIRED", "Срок промокода истёк")
    if promo.max_uses is not None and promo.uses_count >= promo.max_uses:
        raise AppError("PROMO_EXHAUSTED", "Промокод больше не действует")
    used = db.scalar(
        select(func.count()).select_from(PromoRedemption).where(
            PromoRedemption.promo_id == promo.id, PromoRedemption.user_id == user.id
        )
    ) or 0
    if used >= max(1, promo.per_user or 1):
        raise AppError("PROMO_USED", "Вы уже использовали этот промокод")
    if promo.kind == "product" and promo.product_id:
        if not product or product.id != promo.product_id:
            name = promo.product.name if getattr(promo, "product", None) else "выбранного товара"
            raise AppError("PROMO_WRONG_PRODUCT", f"Промокод только для «{name}»")
    if total is not None and money(promo.min_order) > 0 and money(total) < money(promo.min_order):
        raise AppError("PROMO_MIN_ORDER", f"Минимальная сумма заказа {money(promo.min_order):.2f} ₽")


def compute_discount(promo: PromoCode, total: Decimal) -> Decimal:
    base = money(total)
    if base <= 0:
        return money(0)
    if promo.amount_type == "percent":
        return min(base, percent_of(base, promo.amount))
    return min(base, money(promo.amount))


def preview(db: Session, user: User, code: str, *, product: Product | None = None, total: Decimal | None = None) -> dict:
    normalized = normalize_code(code)
    if not CODE_RE.match(normalized):
        raise AppError("INVALID_PROMO", "Некорректный промокод")
    promo = db.scalar(select(PromoCode).options(selectinload(PromoCode.product)).where(PromoCode.code == normalized))
    if not promo:
        raise NotFoundError("Промокод не найден")
    assert_redeemable(db, promo, user, product=product, total=total if promo.kind != "balance" else None)
    if promo.kind == "balance":
        return {
            "valid": True,
            "kind": promo.kind,
            "amount_type": promo.amount_type,
            "amount": f"{money(promo.amount):.2f}",
            "discount": "0.00",
            "new_total": f"{money(total):.2f}" if total is not None else None,
            "message": f"Начислит {money(promo.amount):.2f} ₽ на баланс",
        }
    discount = compute_discount(promo, money(total or 0))
    new_total = money(money(total or 0) - discount)
    label = f"{money(promo.amount):.0f}%" if promo.amount_type == "percent" else f"{money(promo.amount):.2f} ₽"
    return {
        "valid": True,
        "kind": promo.kind,
        "amount_type": promo.amount_type,
        "amount": f"{money(promo.amount):.2f}",
        "discount": f"{discount:.2f}",
        "new_total": f"{new_total:.2f}",
        "product_id": promo.product_id,
        "message": f"Скидка {label}",
    }


def apply_checkout(db: Session, user: User, code: str | None, product: Product, total: Decimal) -> tuple[Decimal, Decimal, PromoCode | None]:
    if not code:
        return money(total), money(0), None
    normalized = normalize_code(code)
    if not normalized:
        return money(total), money(0), None
    promo = _lock_promo(db, normalized)
    if promo.kind == "balance":
        raise AppError("PROMO_BALANCE_ONLY", "Этот промокод начисляет баланс. Откройте раздел Баланс.")
    assert_redeemable(db, promo, user, product=product, total=total)
    discount = compute_discount(promo, total)
    new_total = money(total - discount)
    return new_total, discount, promo


def consume(db: Session, promo: PromoCode, user: User, *, amount: Decimal, order_id: int | None = None) -> None:
    promo.uses_count = int(promo.uses_count or 0) + 1
    db.add(PromoRedemption(promo_id=promo.id, user_id=user.id, order_id=order_id, amount=money(amount)))


def redeem_balance(db: Session, user: User, code: str) -> dict:
    from app.services.orders import _lock_balance

    normalized = normalize_code(code)
    if not CODE_RE.match(normalized):
        raise AppError("INVALID_PROMO", "Некорректный промокод")
    promo = _lock_promo(db, normalized)
    if promo.kind != "balance":
        raise AppError("PROMO_NOT_BALANCE", "Этот промокод применяется при покупке")
    assert_redeemable(db, promo, user)
    credit = money(promo.amount)
    bal = _lock_balance(db, user.id)
    before = money(bal.amount)
    after = money(before + credit)
    bal.amount = after
    consume(db, promo, user, amount=credit)
    db.add(
        Transaction(
            user_id=user.id,
            type="PROMO",
            amount=credit,
            balance_before=before,
            balance_after=after,
            description=f"Промокод {promo.code}",
            payload={"promo_id": promo.id, "code": promo.code},
        )
    )
    db.commit()
    return {"credited": f"{credit:.2f}", "balance": f"{after:.2f}", "code": promo.code}
