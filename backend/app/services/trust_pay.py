from __future__ import annotations

import logging
import secrets
import time
from datetime import timedelta, timezone
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.money import money, percent_of
from app.models import Payment, Transaction, User
from app.models.entities import utcnow
from app.services.audit import write_audit
from app.services.orders import _lock_balance

log = logging.getLogger("PAYMENTS")

OPEN = {"pending", "processing"}
_rate: dict[str, list[float]] = {}


def _rate_ok(key: str, limit: int = 10, window: float = 60.0) -> bool:
    now = time.monotonic()
    hits = [t for t in _rate.get(key, []) if now - t < window]
    if len(hits) >= limit:
        _rate[key] = hits
        return False
    hits.append(now)
    _rate[key] = hits
    return True


def digits(card: str) -> str:
    return "".join(ch for ch in (card or "") if ch.isdigit())


def mask_card(card: str) -> str:
    d = digits(card)
    if len(d) < 8:
        return "•••• ••••"
    return f"{d[:4]} •••• •••• {d[-4:]}"


def copy_card(card: str) -> str:
    d = digits(card)
    return " ".join(d[i : i + 4] for i in range(0, len(d), 4))


def yoomoney_url(amount) -> str:
    """Amount is mandatory — never emit /0."""
    settings = get_settings()
    wallet = digits(settings.yoomoney_wallet) or "4100119621450464"
    total = money(amount)
    if total <= 0:
        raise AppError("AMOUNT_REQUIRED", "Укажите сумму пополнения, прежде чем открыть оплату")
    if total == total.to_integral_value():
        amt = str(int(total))
    else:
        amt = f"{total:.2f}"
    return f"https://yoomoney.ru/to/{wallet}/{amt}"


def shop_origin() -> str:
    raw = (get_settings().telegram_webapp_url or "").strip()
    return raw.split("#")[0].split("?")[0].rstrip("/")


def pay_url(public_id: str) -> str:
    origin = shop_origin()
    path = f"/pay/{public_id}"
    return f"{origin}{path}" if origin else path


def _public_id() -> str:
    return "TP-" + secrets.token_hex(4).upper()


def _aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _expire(pay: Payment) -> Payment:
    exp = _aware(pay.expires_at)
    if pay.status == "pending" and exp and exp < utcnow():
        pay.status = "expired"
    return pay


def topup_reply(pay: Payment) -> tuple[str, dict | None]:
    page = pay_url(pay.public_id or "")
    ym = yoomoney_url(pay.total)
    text = (
        "TRUST PAY\n"
        f"Сумма пополнения: {money(pay.amount):.2f} ₽\n"
        f"Комиссия: {money(pay.fee):.2f} ₽\n"
        f"К оплате: {money(pay.total):.2f} ₽\n"
        "Нажмите кнопку ниже, чтобы перейти к оплате."
    )
    buttons: list[list[dict]] = []
    if page.startswith("https://"):
        buttons.append([{"text": "Перейти к оплате", "web_app": {"url": page}}])
    buttons.append([{"text": "Оплатить ЮMoney", "url": ym}])
    return text, {"inline_keyboard": buttons}


def payment_public(pay: Payment, *, include_card: bool = False, user: User | None = None) -> dict:
    settings = get_settings()
    _expire(pay)
    card = copy_card(settings.trust_pay_card_number)
    data = {
        "id": pay.id,
        "public_id": pay.public_id,
        "amount": f"{money(pay.amount):.2f}",
        "fee": f"{money(pay.fee):.2f}",
        "total": f"{money(pay.total):.2f}",
        "currency": pay.currency or "RUB",
        "status": pay.status,
        "created_at": pay.created_at.isoformat() if pay.created_at else None,
        "paid_at": pay.paid_at.isoformat() if pay.paid_at else None,
        "expires_at": pay.expires_at.isoformat() if pay.expires_at else None,
        "pay_url": pay_url(pay.public_id or ""),
        "yoomoney_url": yoomoney_url(pay.total),
        "min_amount": settings.trust_pay_min_amount,
        "fee_percent": settings.trust_pay_fee_percent,
        "card_masked": mask_card(settings.trust_pay_card_number),
        "card_holder": settings.trust_pay_card_holder or None,
    }
    if include_card:
        data["card_copy"] = card
        data["card_number"] = card
    if user is not None:
        data["telegram_id"] = user.telegram_id
        data["username"] = user.username
        data["first_name"] = user.first_name
        data["user_id"] = user.id
    return data


def create_payment(db: Session, user: User, amount, *, actor_id: int | None = None) -> Payment:
    if not _rate_ok(f"create:{user.id}"):
        raise AppError("RATE_LIMIT", "Слишком много попыток, подождите минуту", 429)
    settings = get_settings()
    amt = money(amount)
    minimum = money(settings.trust_pay_min_amount)
    if amt < minimum:
        raise AppError("MIN_AMOUNT", "Минимальная сумма пополнения — 30 ₽")
    fee = percent_of(amt, settings.trust_pay_fee_percent)
    total = money(amt + fee)
    pid = _public_id()
    while db.scalar(select(Payment.id).where(Payment.public_id == pid)):
        pid = _public_id()
    pay = Payment(
        public_id=pid,
        user_id=user.id,
        provider="trust_pay",
        amount=amt,
        fee=fee,
        total=total,
        currency="RUB",
        status="pending",
        credited=False,
        expires_at=utcnow() + timedelta(minutes=settings.trust_pay_expire_minutes),
        payload={"source": "trust_pay", "yoomoney_url": yoomoney_url(total)},
    )
    db.add(pay)
    write_audit(
        db,
        "trust_pay.create",
        actor_id=actor_id or user.id,
        entity="payment",
        entity_id=pid,
        payload={"amount": str(amt), "fee": str(fee), "total": str(total)},
    )
    db.commit()
    db.refresh(pay)
    log.info("created %s amount=%s total=%s user=%s", pid, amt, total, user.id)
    return pay


def get_owned(db: Session, public_id: str, user: User) -> Payment:
    pay = db.scalar(select(Payment).where(Payment.public_id == public_id))
    if not pay:
        raise NotFoundError("Платёж не найден")
    _expire(pay)
    staff = user.role in {"MANAGER", "ADMIN", "SUPERADMIN"}
    if pay.user_id != user.id and not staff:
        raise ForbiddenError("Этот платёж принадлежит другому пользователю")
    return pay


def mark_user_paid(db: Session, pay: Payment, user: User) -> Payment:
    if not _rate_ok(f"paid:{user.id}:{pay.public_id}", limit=8, window=30):
        raise AppError("RATE_LIMIT", "Слишком много попыток, подождите", 429)
    _expire(pay)
    if pay.status == "paid":
        return pay
    if pay.status not in OPEN:
        raise AppError("INVALID_STATUS", "Этот платёж нельзя подтвердить")
    if pay.user_id != user.id:
        raise ForbiddenError("Этот платёж принадлежит другому пользователю")
    pay.status = "processing"
    write_audit(db, "trust_pay.user_paid", actor_id=user.id, entity="payment", entity_id=pay.public_id)
    db.commit()
    db.refresh(pay)
    return pay


def confirm_payment(db: Session, pay: Payment, actor: User) -> Payment:
    stmt = select(Payment).where(Payment.id == pay.id)
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    locked = db.scalar(stmt)
    if not locked:
        raise NotFoundError("Платёж не найден")
    _expire(locked)
    if locked.credited or locked.status == "paid":
        return locked
    if locked.status not in OPEN:
        raise AppError("INVALID_STATUS", "Этот платёж нельзя подтвердить")

    dup = db.scalar(
        select(Transaction.id).where(
            Transaction.user_id == locked.user_id,
            Transaction.type == "DEPOSIT",
            Transaction.description == f"Trust Pay · {locked.public_id}",
        )
    )
    if dup:
        locked.status = "paid"
        locked.credited = True
        db.commit()
        db.refresh(locked)
        return locked

    bal = _lock_balance(db, locked.user_id)
    before = money(bal.amount)
    credit = money(locked.amount)
    after = money(before + credit)
    bal.amount = after
    locked.status = "paid"
    locked.credited = True
    locked.paid_at = utcnow()
    locked.confirmed_by = actor.id
    db.add(
        Transaction(
            user_id=locked.user_id,
            type="DEPOSIT",
            amount=credit,
            balance_before=before,
            balance_after=after,
            description=f"Trust Pay · {locked.public_id}",
            payload={"payment_id": locked.public_id, "fee": str(locked.fee), "total": str(locked.total)},
        )
    )
    write_audit(
        db,
        "trust_pay.confirm",
        actor_id=actor.id,
        entity="payment",
        entity_id=locked.public_id,
        payload={"amount": str(credit)},
    )
    db.commit()
    db.refresh(locked)
    _notify_paid(db, locked, after)
    return locked


def fail_payment(db: Session, pay: Payment, actor: User) -> Payment:
    if pay.status == "paid" or pay.credited:
        raise AppError("INVALID_STATUS", "Оплаченный платёж нельзя отклонить")
    pay.status = "failed"
    write_audit(db, "trust_pay.fail", actor_id=actor.id, entity="payment", entity_id=pay.public_id)
    db.commit()
    db.refresh(pay)
    return pay


def _notify_paid(db: Session, pay: Payment, balance_after: Decimal) -> None:
    user = db.get(User, pay.user_id)
    if not user or not user.telegram_id:
        return
    settings = get_settings()
    if not settings.telegram_bot_token:
        return
    text = (
        "TRUST PAY\n"
        "Платёж успешно подтверждён.\n"
        f"Пополнение: {money(pay.amount):.2f} ₽\n"
        f"Комиссия: {money(pay.fee):.2f} ₽\n"
        f"ID платежа: {pay.public_id}\n"
        f"Баланс: {money(balance_after):.2f} ₽"
    )
    try:
        httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": user.telegram_id, "text": text},
            timeout=15,
        )
    except Exception as exc:
        log.warning("telegram notify failed payment=%s", pay.public_id)
        del exc
