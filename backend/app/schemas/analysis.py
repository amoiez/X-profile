"""Request/response schemas for the analysis API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.validation import normalize_username


class AnalysisCreateRequest(BaseModel):
    username: str = Field(..., max_length=64, examples=["@example"])
    post_limit: int = Field(
        default=settings.x_default_post_limit,
        ge=1,
        le=settings.x_max_post_limit,
    )
    timezone: str = Field(default=settings.default_timezone, max_length=64)
    force_refresh: bool = False

    @field_validator("username")
    @classmethod
    def _validate_username(cls, v: str) -> str:
        # Raises AppError(INVALID_USERNAME) which the API maps to a 400.
        return normalize_username(v)


class JobSummary(BaseModel):
    id: str
    username: str
    status: str
    progress: int
    current_stage: str | None
    requested_post_limit: int
    actual_post_count: int
    data_source: str
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    period_start: datetime | None
    period_end: datetime | None

    model_config = {"from_attributes": True}


class ProgressResponse(BaseModel):
    id: str
    status: str
    progress: int
    current_stage: str | None
    error_code: str | None = None
    error_message: str | None = None


class ResultsResponse(BaseModel):
    job: JobSummary
    profile: dict
    activity_metrics: dict
    content_metrics: dict
    sentiment_metrics: dict
    engagement_metrics: dict
    pattern_metrics: dict
    summary: dict
    data_quality: dict
    methodology_version: str


class PaginatedJobs(BaseModel):
    items: list[JobSummary]
    total: int
    page: int
    page_size: int
