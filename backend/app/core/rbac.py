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
