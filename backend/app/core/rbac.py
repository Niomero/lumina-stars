from enum import Enum

from app.core.errors import ForbiddenError


class Role(str, Enum):
    USER = "USER"
    MIRROR_OWNER = "MIRROR_OWNER"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"
    SUPERADMIN = "SUPERADMIN"


PERMISSIONS: dict[str, set[str]] = {
    Role.USER: {
        "catalog.read",
        "orders.own",
        "balance.own",
        "profile.own",
        "referrals.own",
    },
    Role.MIRROR_OWNER: {
        "catalog.read",
        "orders.own",
        "balance.own",
        "profile.own",
        "referrals.own",
        "mirrors.own.read",
        "mirrors.own.write",
        "analytics.own",
        "orders.mirror.read",
    },
    Role.MANAGER: {
        "catalog.read",
        "orders.own",
        "balance.own",
        "profile.own",
        "referrals.own",
        "users.read",
        "orders.read",
        "products.read",
        "promos.read",
        "mirrors.read",
        "analytics.read",
    },
    Role.ADMIN: {
        "catalog.read",
        "orders.own",
        "balance.own",
        "profile.own",
        "referrals.own",
        "users.read",
        "users.write",
        "orders.read",
        "orders.write",
        "balance.adjust",
        "products.read",
        "products.write",
        "promos.read",
        "promos.write",
        "mirrors.read",
        "mirrors.write",
        "analytics.read",
        "audit.read",
    },
    Role.SUPERADMIN: {"*"},
}


def has_permission(role: str, permission: str) -> bool:
    granted = PERMISSIONS.get(role, set())
    return "*" in granted or permission in granted


def require_permission(role: str, permission: str) -> None:
    if not has_permission(role, permission):
        raise ForbiddenError("Недостаточно прав")


STAFF_ROLES = {Role.MANAGER.value, Role.ADMIN.value, Role.SUPERADMIN.value}
ASSIGNABLE_ROLES = {Role.USER.value, Role.MANAGER.value, Role.ADMIN.value}


def is_owner_telegram(telegram_id) -> bool:
    from app.core.config import get_settings

    if telegram_id is None:
        return False
    try:
        return int(telegram_id) == int(get_settings().owner_telegram_id)
    except (TypeError, ValueError):
        return False
