"""Cached public X profile data."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import (
    Base,
    PortableJSON,
    created_at_col,
    updated_at_col,
    uuid_pk,
)


class XProfile(Base):
    __tablename__ = "x_profiles"

    id: Mapped[str] = uuid_pk()
    platform_user_id: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    username: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Full public profile blob (bio, metrics, verification, image url, ...).
    public_profile_data: Mapped[dict] = mapped_column(
        PortableJSON, default=dict, nullable=False
    )
    last_retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    jobs: Mapped[list["AnalysisJob"]] = relationship(  # noqa: F821
        back_populates="profile"
    )
