from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import AdminLocked, AuthError, ForbiddenError
from app.core.rbac import STAFF_ROLES, Role, require_permission
from app.core.security import decode_access_token, decode_admin_token
from app.db.session import get_db
from app.models import User


def get_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError()
    return authorization.split(" ", 1)[1].strip()


def get_current_user(db: Session = Depends(get_db), token: str = Depends(get_token)) -> User:
    payload = decode_access_token(token)
    user_id = int(payload.get("sub") or 0)
    user = db.get(User, user_id)
    if not user:
        raise AuthError("Пользователь не найден")
    if user.is_blocked:
        raise ForbiddenError("Аккаунт заблокирован")
    return user


STAFF_UNLOCK_ROLES = STAFF_ROLES | {Role.MIRROR_OWNER.value}


def verify_admin_unlock(user: User, unlock: str | None) -> None:
    if user.role not in STAFF_UNLOCK_ROLES:
        raise ForbiddenError("Недостаточно прав")
    if not unlock:
        raise AdminLocked()
    payload = decode_admin_token(unlock)
    if int(payload.get("sub") or 0) != user.id:
        raise AdminLocked("Сессия администратора не совпадает")


def require(permission: str):
    def _inner(
        user: User = Depends(get_current_user),
        unlock: str | None = Header(default=None, alias="X-Admin-Unlock"),
    ) -> User:
        require_permission(user.role, permission)
        verify_admin_unlock(user, unlock)
        return user

    return _inner


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role not in STAFF_UNLOCK_ROLES:
        raise ForbiddenError("Недостаточно прав")
    return user
