from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_code(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_code(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return ""


def hash_code(plain: str) -> str:
    return hashlib.sha256(plain.strip().encode()).hexdigest()


def mask_code(plain: str) -> str:
    raw = (plain or "").strip()
    if len(raw) <= 4:
        return "••••"
    return f"{'•' * max(4, len(raw) - 4)}{raw[-4:]}"
