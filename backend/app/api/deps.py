"""Shared API dependencies: optional/required auth and admin guard.

Auth is optional across the app: endpoints work anonymously, but if a valid
bearer token is supplied the request is scoped to that user. This lets the
prototype run without login while supporting full user ownership when enabled.
"""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.core.security import decode_token
from app.database.session import get_session
from app.models import User
from app.models.user import UserRole


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


async def get_optional_user(
    request: Request, session: AsyncSession = Depends(get_session)
) -> User | None:
    token = _bearer_token(request)
    if not token:
        return None
    payload = decode_token(token, expected_type="access")
    if not payload:
        return None
    user = await session.get(User, payload.get("sub"))
    return user


async def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Authentication required.", http_status=401)
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Admin privileges required.", http_status=403)
    return user
