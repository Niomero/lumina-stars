from abc import ABC, abstractmethod
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.money import money
from app.models import Balance, Payment, Transaction
from app.services.audit import write_audit
from app.services.orders import _lock_balance


class PaymentProvider(ABC):
    @abstractmethod
    def deposit(self, db: Session, user_id: int, amount: Decimal, actor_id: int | None = None) -> Payment:
        raise NotImplementedError


class DemoPaymentProvider(PaymentProvider):
    def deposit(self, db: Session, user_id: int, amount: Decimal, actor_id: int | None = None) -> Payment:
        amt = money(amount)
        if amt <= 0:
            raise ValueError("amount")
        bal = _lock_balance(db, user_id)
        before = money(bal.amount)
        after = money(before + amt)
        bal.amount = after
        pay = Payment(user_id=user_id, provider="demo", amount=amt, status="COMPLETED")
        db.add(pay)
        db.add(
            Transaction(
                user_id=user_id,
                type="DEPOSIT",
                amount=amt,
                balance_before=before,
                balance_after=after,
                description="Пополнение баланса",
            )
        )
        write_audit(db, "balance.deposit", actor_id=actor_id or user_id, entity="user", entity_id=user_id, payload={"amount": str(amt)})
        db.commit()
        db.refresh(pay)
        return pay


class FuturePaymentProvider(PaymentProvider):
    def deposit(self, db: Session, user_id: int, amount: Decimal, actor_id: int | None = None) -> Payment:
        raise NotImplementedError("Реальный платёжный провайдер ещё не подключён")


def get_payment_provider() -> PaymentProvider:
    return DemoPaymentProvider()
