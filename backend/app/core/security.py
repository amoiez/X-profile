"""Password hashing (Argon2) and JWT token helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()
_ALGO = "HS256"

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:  # noqa: BLE001 - malformed hash etc.
        return False


def _create_token(
    subject: str, token_type: TokenType, *, role: str, expires: timedelta
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=_ALGO)


def create_access_token(subject: str, role: str = "user") -> str:
    return _create_token(
        subject, "access", role=role,
        expires=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str, role: str = "user") -> str:
    return _create_token(
        subject, "refresh", role=role,
        expires=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[_ALGO])
    except jwt.PyJWTError:
        return None
    if expected_type and payload.get("type") != expected_type:
        return None
    return payload
