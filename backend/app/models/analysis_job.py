"""Analysis job model — one per analysis request."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import (
    Base,
    GUID,
    created_at_col,
    uuid_pk,
)


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    profile_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("x_profiles.id", ondelete="SET NULL"), index=True, nullable=True
    )

    username: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=JobStatus.PENDING.value, index=True, nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)

    requested_post_limit: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    actual_post_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)

    period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    data_source: Mapped[str] = mapped_column(String(16), default="mock", nullable=False)

    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = created_at_col()
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User | None"] = relationship(back_populates="jobs")  # noqa: F821
    profile: Mapped["XProfile | None"] = relationship(back_populates="jobs")  # noqa: F821
    result: Mapped["AnalysisResult | None"] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )
    reports: Mapped[list["Report"]] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan"
    )
