"""Analysis result model — computed metrics for a completed job."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import (
    GUID,
    Base,
    PortableJSON,
    created_at_col,
    uuid_pk,
)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = uuid_pk()
    job_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    activity_metrics: Mapped[dict] = mapped_column(PortableJSON, default=dict, nullable=False)
    content_metrics: Mapped[dict] = mapped_column(PortableJSON, default=dict, nullable=False)
    sentiment_metrics: Mapped[dict] = mapped_column(PortableJSON, default=dict, nullable=False)
    engagement_metrics: Mapped[dict] = mapped_column(PortableJSON, default=dict, nullable=False)
    pattern_metrics: Mapped[dict] = mapped_column(PortableJSON, default=dict, nullable=False)
    summary: Mapped[dict] = mapped_column(PortableJSON, default=dict, nullable=False)
    data_quality: Mapped[dict] = mapped_column(PortableJSON, default=dict, nullable=False)

    methodology_version: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = created_at_col()

    job: Mapped[AnalysisJob] = relationship(back_populates="result")  # noqa: F821
