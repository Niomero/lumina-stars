from __future__ import annotations

import secrets
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthError, ForbiddenError
from app.core.money import money
from app.core.rbac import Role, is_owner_telegram
from app.core.security import create_access_token, validate_telegram_init_data
from app.models import Balance, Referral, Transaction, User
from app.services.audit import write_audit


def _unique_code(db: Session) -> str:
    for _ in range(12):
        code = secrets.token_hex(3).upper()
        exists = db.scalar(select(User.id).where(User.referral_code == code))
        if not exists:
            return code
    return secrets.token_hex(4).upper()


def _first_user_is_superadmin(db: Session) -> bool:
    count = db.scalar(select(func.count()).select_from(User)) or 0
    return count == 0


def provision_user(
    db: Session,
    *,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    photo_url: str | None,
    start_param: str | None = None,
    mirror_id: int | None = None,
) -> User:
    settings = get_settings()
    user = db.scalar(select(User).where(User.telegram_id == telegram_id))
    created = False
    if user is None:
        created = True
        role = Role.USER.value
        if _first_user_is_superadmin(db) or is_owner_telegram(telegram_id):
            role = Role.SUPERADMIN.value
        referred_by = None
        if start_param and start_param.startswith("ref_"):
            owner = db.scalar(select(User).where(User.referral_code == start_param[4:].upper()))
            if owner:
                referred_by = owner.id
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            photo_url=photo_url,
            role=role,
            referral_code=_unique_code(db),
            referred_by=referred_by,
            mirror_id=mirror_id,
        )
        db.add(user)
        db.flush()
        bonus = money(settings.bootstrap_balance_rub) if role == Role.SUPERADMIN.value else money(0)
        db.add(Balance(user_id=user.id, amount=bonus, currency="RUB"))
        if bonus > 0:
            db.add(
                Transaction(
                    user_id=user.id,
                    type="BONUS",
                    amount=bonus,
                    balance_before=Decimal("0.00"),
                    balance_after=bonus,
                    description="Стартовый бонус",
                )
            )
        if referred_by:
            db.add(Referral(owner_user_id=referred_by, invited_user_id=user.id))
        write_audit(db, "user.create", actor_id=user.id, entity="user", entity_id=user.id)
    else:
        if user.is_blocked:
            raise ForbiddenError("Аккаунт заблокирован")
        user.username = username or user.username
        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        user.photo_url = photo_url or user.photo_url
        if mirror_id and not user.mirror_id:
            user.mirror_id = mirror_id
        if is_owner_telegram(user.telegram_id):
            user.role = Role.SUPERADMIN.value
    db.flush()
    write_audit(db, "login", actor_id=user.id, entity="user", entity_id=user.id, payload={"created": created})
    return user


def login_telegram(db: Session, init_data: str, mirror_id: int | None = None) -> tuple[User, str]:
    data = validate_telegram_init_data(init_data)
    tg = data["user"]
    user = provision_user(
        db,
        telegram_id=int(tg["id"]),
        username=tg.get("username"),
        first_name=tg.get("first_name"),
        last_name=tg.get("last_name"),
        photo_url=tg.get("photo_url"),
        start_param=data.get("start_param"),
        mirror_id=mirror_id,
    )
    db.commit()
    db.refresh(user)
    return user, create_access_token(user.id, {"role": user.role})


def login_demo(db: Session, display_name: str = "Lumina") -> tuple[User, str]:
    settings = get_settings()
    if not settings.demo_login_enabled:
        raise AuthError("Демо-вход отключён")
    user = provision_user(
        db,
        telegram_id=1,
        username="lumina",
        first_name=display_name,
        last_name="Admin",
        photo_url=None,
    )
    db.commit()
    db.refresh(user)
    return user, create_access_token(user.id, {"role": user.role, "demo": True})
