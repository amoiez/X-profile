"""User registration and authentication."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models import User
from app.models.user import UserRole


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    res = await session.execute(select(User).where(User.email == email.lower()))
    return res.scalar_one_or_none()


async def register_user(
    session: AsyncSession, *, email: str, password: str, role: UserRole = UserRole.USER
) -> User:
    user = User(email=email.lower(), password_hash=hash_password(password), role=role)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate(session: AsyncSession, *, email: str, password: str) -> User | None:
    user = await get_by_email(session, email)
    if user is None or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
