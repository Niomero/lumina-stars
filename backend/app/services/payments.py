"""Trust Pay is the only payment provider. Instant demo deposits are removed."""

from app.core.errors import AppError


def deposit(*_args, **_kwargs):
    raise AppError("TRUST_PAY_ONLY", "Пополнение только через Trust Pay")
