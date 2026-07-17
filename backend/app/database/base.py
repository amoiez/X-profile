"""SQLAlchemy declarative base and shared column types.

A portable JSON type is used so the same models work on PostgreSQL (JSONB)
and SQLite (JSON) for local development and tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy.types import JSON, TypeDecorator


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class PortableJSON(TypeDecorator):
    """JSONB on PostgreSQL, plain JSON elsewhere (e.g. SQLite)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class GUID(TypeDecorator):
    """Platform-independent UUID stored as a 36-char string."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return str(value)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid_pk():
    return mapped_column(GUID(), primary_key=True, default=generate_uuid)


def created_at_col():
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


def updated_at_col():
    return mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
