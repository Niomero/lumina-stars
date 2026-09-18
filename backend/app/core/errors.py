from typing import Any, Optional


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class AuthError(AppError):
    def __init__(self, message: str = "Требуется авторизация"):
        super().__init__("UNAUTHORIZED", message, 401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Недостаточно прав"):
        super().__init__("FORBIDDEN", message, 403)


class NotFoundError(AppError):
    def __init__(self, message: str = "Не найдено"):
        super().__init__("NOT_FOUND", message, 404)


class InsufficientBalance(AppError):
    def __init__(self, message: str = "Недостаточно средств"):
        super().__init__("INSUFFICIENT_BALANCE", message, 402)
