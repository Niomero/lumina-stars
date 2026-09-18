class TgStarsError(Exception):
    def __init__(self, message: str, status_code: int | None = None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class TgStarsAuthError(TgStarsError):
    pass


class TgStarsUnavailable(TgStarsError):
    pass
