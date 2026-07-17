"""Authentication endpoints (optional local auth)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError, ErrorCode
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.database.session import get_session
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens_for(user: User) -> TokenResponse:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return TokenResponse(
        access_token=create_access_token(user.id, role),
        refresh_token=create_refresh_token(user.id, role),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    existing = await auth_service.get_by_email(session, payload.email)
    if existing is not None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Email already registered.", http_status=409)
    user = await auth_service.register_user(
        session, email=payload.email, password=payload.password
    )
    return _tokens_for(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    user = await auth_service.authenticate(
        session, email=payload.email, password=payload.password
    )
    if user is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid email or password.", http_status=401)
    return _tokens_for(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    data = decode_token(payload.refresh_token, expected_type="refresh")
    if not data:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid refresh token.", http_status=401)
    user = await session.get(User, data.get("sub"))
    if user is None:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid refresh token.", http_status=401)
    return _tokens_for(user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
