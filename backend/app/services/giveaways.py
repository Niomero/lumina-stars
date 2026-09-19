from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, NotFoundError
from app.core.money import money
from app.models import (
    DigitalProduct,
    Giveaway,
    GiveawayParticipant,
    GiveawayWinner,
    Transaction,
    User,
)
from app.models.entities import utcnow
from app.services.audit import write_audit
from app.services.notify import notify_owner, send_telegram
from app.services.orders import _lock_balance


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def participant_count(db: Session, giveaway_id: int) -> int:
    return int(
        db.scalar(select(func.count()).select_from(GiveawayParticipant).where(GiveawayParticipant.giveaway_id == giveaway_id))
        or 0
    )


def giveaway_public(db: Session, g: Giveaway, *, user_id: int | None = None) -> dict:
    joined = False
    if user_id:
        joined = bool(
            db.scalar(
                select(GiveawayParticipant.id).where(
                    GiveawayParticipant.giveaway_id == g.id, GiveawayParticipant.user_id == user_id
                )
            )
        )
    prize = None
    if g.reward_type == "balance":
        prize = {"type": "balance", "amount": f"{money(g.reward_amount):.2f}"}
    elif g.product:
        prize = {"type": "product", "product_id": g.product.id, "name": g.product.name, "face_value": g.product.face_value}
    return {
        "id": g.id,
        "title": g.title,
        "description": g.description,
        "image": g.image or None,
        "reward_type": g.reward_type,
        "prize": prize,
        "winner_count": g.winner_count,
        "finish_type": g.finish_type,
        "finish_at": g.finish_at.isoformat() if g.finish_at else None,
        "max_participants": g.max_participants,
        "participants": participant_count(db, g.id),
        "status": g.status,
        "joined": joined,
        "finished_at": g.finished_at.isoformat() if g.finished_at else None,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }


def validate_payload(db: Session, data: dict) -> None:
    title = (data.get("title") or "").strip()
    if len(title) < 2:
        raise AppError("INVALID_GIVEAWAY", "Укажите название")
    winners = int(data.get("winner_count") or 1)
    if winners < 1:
        raise AppError("INVALID_GIVEAWAY", "Нужен хотя бы один победитель")
    max_p = data.get("max_participants")
    if max_p is not None and int(max_p) < winners:
        raise AppError("INVALID_GIVEAWAY", "Победителей не может быть больше участников")
    finish_type = data.get("finish_type") or "time"
    if finish_type not in {"time", "count"}:
        raise AppError("INVALID_GIVEAWAY", "Завершение: по времени или по числу участников")
    if finish_type == "time":
        finish_at = data.get("finish_at")
        if not finish_at:
            raise AppError("INVALID_GIVEAWAY", "Укажите дату окончания")
        when = _aware(finish_at) if isinstance(finish_at, datetime) else finish_at
        if isinstance(when, datetime) and when <= utcnow():
            raise AppError("INVALID_GIVEAWAY", "Дата окончания уже прошла")
    if finish_type == "count" and not max_p:
        raise AppError("INVALID_GIVEAWAY", "Укажите максимум участников")
    reward_type = data.get("reward_type") or "balance"
    if reward_type == "balance":
        if money(data.get("reward_amount") or 0) <= 0:
            raise AppError("INVALID_GIVEAWAY", "Укажите сумму приза")
    elif reward_type == "product":
        pid = data.get("reward_product_id")
        product = db.get(DigitalProduct, pid) if pid else None
        if not product:
            raise AppError("INVALID_GIVEAWAY", "Выберите товар для приза")
    else:
        raise AppError("INVALID_GIVEAWAY", "Тип приза: товар или баланс")


def join(db: Session, giveaway: Giveaway, user: User) -> Giveaway:
    tick_one(db, giveaway)
    db.refresh(giveaway)
    if giveaway.status != "active":
        raise AppError("GIVEAWAY_CLOSED", "Розыгрыш уже завершён")
    if giveaway.max_participants and participant_count(db, giveaway.id) >= giveaway.max_participants:
        raise AppError("GIVEAWAY_FULL", "Мест больше нет")
    exists = db.scalar(
        select(GiveawayParticipant.id).where(GiveawayParticipant.giveaway_id == giveaway.id, GiveawayParticipant.user_id == user.id)
    )
    if exists:
        raise AppError("ALREADY_JOINED", "Вы уже участвуете")
    db.add(GiveawayParticipant(giveaway_id=giveaway.id, user_id=user.id))
    write_audit(db, "giveaway.join", user.id, "giveaway", giveaway.id)
    db.commit()
    send_telegram(user, f"Вы участвуете в розыгрыше.\n{giveaway.title}")
    tick_one(db, giveaway)
    return giveaway


def tick(db: Session) -> int:
    closed = 0
    now = utcnow()
    active = list(db.scalars(select(Giveaway).where(Giveaway.status == "active")))
    for g in active:
        if tick_one(db, g, now=now):
            closed += 1
    return closed


def tick_one(db: Session, giveaway: Giveaway, now: datetime | None = None) -> bool:
    if giveaway.status != "active":
        return False
    now = now or utcnow()
    due = False
    if giveaway.finish_type == "time" and _aware(giveaway.finish_at) and _aware(giveaway.finish_at) <= now:
        due = True
    if giveaway.finish_type == "count" and giveaway.max_participants:
        if participant_count(db, giveaway.id) >= giveaway.max_participants:
            due = True
    if not due:
        return False
    finish(db, giveaway, method="auto")
    return True


def finish(db: Session, giveaway: Giveaway, *, method: str = "auto", actor_id: int | None = None) -> Giveaway:
    stmt = select(Giveaway).where(Giveaway.id == giveaway.id)
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    locked = db.scalar(stmt)
    if not locked:
        raise NotFoundError("Розыгрыш не найден")
    if locked.status != "active":
        return locked
    locked.status = "finished"
    locked.finished_at = utcnow()
    people = list(db.scalars(select(GiveawayParticipant.user_id).where(GiveawayParticipant.giveaway_id == locked.id)))
    k = min(int(locked.winner_count), len(people))
    picked = secrets.SystemRandom().sample(people, k) if k else []
    for uid in picked:
        winner = GiveawayWinner(
            giveaway_id=locked.id,
            user_id=uid,
            reward_status="pending",
            selection_method="secrets.SystemRandom",
        )
        db.add(winner)
        db.flush()
        _deliver_prize(db, locked, winner)
    write_audit(db, "giveaway.finish", actor_id, "giveaway", locked.id, {"winners": picked, "method": method})
    db.commit()
    db.refresh(locked)
    return locked


def _deliver_prize(db: Session, giveaway: Giveaway, winner: GiveawayWinner) -> None:
    user = db.get(User, winner.user_id)
    if giveaway.reward_type == "balance":
        amount = money(giveaway.reward_amount)
        bal = _lock_balance(db, winner.user_id)
        before = money(bal.amount)
        after = money(before + amount)
        bal.amount = after
        tx = Transaction(
            user_id=winner.user_id,
            type="GIVEAWAY",
            amount=amount,
            balance_before=before,
            balance_after=after,
            description=f"Розыгрыш · {giveaway.title}",
            payload={"giveaway_id": giveaway.id},
        )
        db.add(tx)
        db.flush()
        winner.reward_transaction_id = tx.id
        winner.reward_status = "completed"
        send_telegram(
            user,
            f"Поздравляем! Вы выиграли.\nРозыгрыш: {giveaway.title}\nНа ваш баланс зачислено: {amount:.2f} ₽",
        )
        send_telegram(user, "Ваш приз уже выдан.")
        return
    product = db.get(DigitalProduct, giveaway.reward_product_id) if giveaway.reward_product_id else None
    if not product:
        winner.reward_status = "reward_pending"
        notify_owner(db, f"Не удалось автоматически выдать приз розыгрыша #{giveaway.id}")
        send_telegram(user, "Приз будет выдан после завершения обработки.")
        return
    from app.services.digital import grant_product

    order = grant_product(db, user, product, idempotency_key=f"giveaway-{giveaway.id}-{winner.user_id}")
    winner.digital_order_id = order.id
    if order.status == "completed":
        winner.reward_status = "completed"
        send_telegram(user, f"Поздравляем! Вы выиграли {product.name}. Код в «Мои покупки».")
        send_telegram(user, "Ваш приз уже выдан.")
    else:
        winner.reward_status = "reward_pending"
        send_telegram(user, "Приз будет выдан после завершения обработки.")
        notify_owner(db, f"Не удалось автоматически выдать приз розыгрыша #{giveaway.id} пользователю {winner.user_id}")

def cancel(db: Session, giveaway: Giveaway, actor_id: int) -> Giveaway:
    if giveaway.status == "finished":
        raise AppError("INVALID_STATUS", "Завершённый розыгрыш нельзя отменить")
    giveaway.status = "cancelled"
    write_audit(db, "giveaway.cancel", actor_id, "giveaway", giveaway.id)
    db.commit()
    db.refresh(giveaway)
    return giveaway
