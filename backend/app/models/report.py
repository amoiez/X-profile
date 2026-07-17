"""Report metadata model — points at a generated PDF artifact."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import GUID, Base, utcnow, uuid_pk


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = uuid_pk()
    job_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    format: Mapped[str] = mapped_column(String(16), default="pdf", nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    job: Mapped[AnalysisJob] = relationship(back_populates="reports")  # noqa: F821
