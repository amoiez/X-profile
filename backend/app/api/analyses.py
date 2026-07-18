"""Analysis job endpoints (API v1)."""

import csv
import os
import re
from datetime import UTC, datetime
from io import StringIO

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user
from app.core.errors import AppError, ErrorCode
from app.core.limiter import ANALYSIS_LIMIT, limiter
from app.database.session import get_session
from app.models import User
from app.models.analysis_job import AnalysisJob, JobStatus
from app.providers.mock_x import is_demo_username
from app.providers.base import ProviderPost, ProviderProfile
from app.schemas.analysis import (
    AnalysisCreateRequest,
    ImportedAnalysisRequest,
    JobSummary,
    PaginatedJobs,
    ProgressResponse,
    ResultsResponse,
)
from app.services import job_service, queue, report_service

router = APIRouter(prefix="/analyses", tags=["analyses"])

_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_]+)")
_MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_]{1,15})")
_URL_RE = re.compile(r"https?://[^\s]+")


def _authorize(job: AnalysisJob, user: User | None) -> None:
    """Owned jobs are only visible to their owner; anonymous jobs are open.

    Returns 404 (not 403) for someone else's job so ownership isn't leaked.
    """
    if job.user_id is not None and (user is None or user.id != job.user_id):
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)


@router.post("", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(ANALYSIS_LIMIT)
async def create_analysis(
    request: Request,
    response: Response,
    payload: AnalysisCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
) -> JobSummary:
    from app.core.config import settings

    data_source = "mock" if settings.use_mock_provider else "x_api"
    if (
        data_source == "mock"
        and not settings.allow_arbitrary_mock_profiles
        and not is_demo_username(payload.username)
    ):
        raise AppError(
            ErrorCode.CREDENTIALS_MISSING,
            (
                "Live X API credentials are required to analyze real usernames. "
                "This server is in demo mode; use a demo username such as "
                "sample_user, coffee_lover, news_bot, empty_demo, protected_demo, "
                "suspended_demo, or configure X_PROVIDER=x_api with X_API_BEARER_TOKEN."
            ),
            http_status=503,
        )
    job = await job_service.create_job(
        session,
        username=payload.username,
        post_limit=payload.post_limit,
        tz=payload.timezone,
        data_source=data_source,
        user_id=user.id if user else None,
    )
    await queue.enqueue(job.id)
    return JobSummary.model_validate(job)


@router.post("/import", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(ANALYSIS_LIMIT)
async def create_imported_analysis(
    request: Request,
    response: Response,
    payload: ImportedAnalysisRequest,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
) -> JobSummary:
    from app.services.analysis_runner import complete_supplied_job

    posts = _parse_imported_posts(payload.csv_text)
    profile = ProviderProfile(
        platform_user_id=f"import:{payload.username}",
        username=payload.username,
        display_name=payload.display_name or payload.username,
        followers_count=payload.followers_count,
    )
    job = await job_service.create_job(
        session,
        username=payload.username,
        post_limit=len(posts),
        tz=payload.timezone,
        data_source="import",
        user_id=user.id if user else None,
    )
    await complete_supplied_job(job.id, profile=profile, posts=posts, data_source="import")
    await session.refresh(job)
    return JobSummary.model_validate(job)


@router.get("/{job_id}", response_model=JobSummary)
async def get_analysis(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
) -> JobSummary:
    job = await job_service.get_job(session, job_id)
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
    _authorize(job, user)
    return JobSummary.model_validate(job)


@router.get("/{job_id}/progress", response_model=ProgressResponse)
async def get_progress(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
) -> ProgressResponse:
    job = await job_service.get_job(session, job_id)
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
    _authorize(job, user)
    return ProgressResponse(
        id=job.id,
        status=job.status,
        progress=job.progress,
        current_stage=job.current_stage,
        error_code=job.error_code,
        error_message=job.error_message,
    )


@router.get("/{job_id}/results", response_model=ResultsResponse)
async def get_results(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
) -> ResultsResponse:
    job = await job_service.get_job(session, job_id)
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
    _authorize(job, user)
    if job.status == JobStatus.FAILED.value:
        raise AppError(
            ErrorCode(job.error_code) if job.error_code in ErrorCode._value2member_map_
            else ErrorCode.ANALYSIS_FAILED,
            job.error_message or "Analysis failed.",
            http_status=409,
        )
    if job.status != JobStatus.COMPLETED.value:
        # Not ready yet.
        raise AppError(
            ErrorCode.ANALYSIS_FAILED,
            "Analysis is not complete yet.",
            http_status=409,
        )

    result = await job_service.get_result(session, job_id)
    if result is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)

    profile = {}
    if job.profile_id:
        from app.models import XProfile

        prof = await session.get(XProfile, job.profile_id)
        if prof:
            profile = prof.public_profile_data

    return ResultsResponse(
        job=JobSummary.model_validate(job),
        profile=profile,
        activity_metrics=result.activity_metrics,
        content_metrics=result.content_metrics,
        sentiment_metrics=result.sentiment_metrics,
        engagement_metrics=result.engagement_metrics,
        pattern_metrics=result.pattern_metrics,
        summary=result.summary,
        data_quality=result.data_quality,
        methodology_version=result.methodology_version,
    )


@router.get("", response_model=PaginatedJobs)
async def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
) -> PaginatedJobs:
    rows, total = await job_service.list_jobs(
        session,
        owner_id=user.id if user else None,
        only_unowned=user is None,
        page=page,
        page_size=page_size,
    )
    return PaginatedJobs(
        items=[JobSummary.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}/report.pdf")
async def download_report(
    job_id: str,
    force: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
) -> FileResponse:
    job = await job_service.get_job(session, job_id)
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
    _authorize(job, user)
    path = await report_service.generate_pdf_for_job(session, job_id, force=force)
    if not os.path.exists(path):
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"x-behavior-report-{job_id[:8]}.pdf",
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
) -> Response:
    job = await job_service.get_job(session, job_id)
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
    _authorize(job, user)
    await job_service.delete_job(session, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{job_id}/refresh", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
async def refresh_analysis(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    user: User | None = Depends(get_optional_user),
) -> JobSummary:
    old = await job_service.get_job(session, job_id)
    if old is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
    _authorize(old, user)
    new_job = await job_service.create_job(
        session,
        username=old.username,
        post_limit=old.requested_post_limit,
        tz=old.timezone,
        user_id=old.user_id,
        data_source=old.data_source,
    )
    await queue.enqueue(new_job.id)
    return JobSummary.model_validate(new_job)


def _parse_imported_posts(csv_text: str) -> list[ProviderPost]:
    sample = csv_text.lstrip("\ufeff").strip()
    try:
        reader = csv.DictReader(StringIO(sample))
        rows = list(reader)
    except csv.Error as exc:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Could not parse CSV data.") from exc

    if not rows or not reader.fieldnames:
        raise AppError(ErrorCode.VALIDATION_ERROR, "CSV must include a header row and at least one post.")

    posts: list[ProviderPost] = []
    for index, row in enumerate(rows, start=1):
        normalized = {str(k).strip().lower(): (v or "").strip() for k, v in row.items() if k}
        text = _first(normalized, "text", "tweet", "post", "content", "full_text")
        if not text:
            raise AppError(ErrorCode.VALIDATION_ERROR, f"Row {index} is missing text.")

        created_at = _parse_datetime(_first(normalized, "created_at", "date", "timestamp", "time"))
        if created_at is None:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                f"Row {index} is missing a valid created_at/date/timestamp value.",
            )
        post_type = _choice(_first(normalized, "post_type", "type"), {"original", "reply", "repost", "quote"}, "original")
        urls = _split_values(_first(normalized, "urls", "url", "links")) or _URL_RE.findall(text)
        media_type = _choice(_first(normalized, "media_type", "media"), {"none", "image", "video", "gif", "poll", "link"}, "link" if urls else "none")

        posts.append(
            ProviderPost(
                post_id=_first(normalized, "post_id", "id", "tweet_id") or f"import-{index}",
                text=text,
                created_at=created_at,
                lang=_first(normalized, "lang", "language") or None,
                post_type=post_type,
                media_type=media_type,
                like_count=_to_int(_first(normalized, "like_count", "likes")),
                reply_count=_to_int(_first(normalized, "reply_count", "replies")),
                repost_count=_to_int(_first(normalized, "repost_count", "retweets", "reposts")),
                quote_count=_to_int(_first(normalized, "quote_count", "quotes")),
                hashtags=_split_values(_first(normalized, "hashtags")) or _HASHTAG_RE.findall(text),
                mentions=_split_values(_first(normalized, "mentions")) or _MENTION_RE.findall(text),
                urls=urls,
                conversation_id=_first(normalized, "conversation_id") or None,
                in_reply_to_user_id=_first(normalized, "in_reply_to_user_id") or None,
            )
        )

    return posts


def _first(row: dict[str, str], *names: str) -> str:
    for name in names:
        if row.get(name):
            return row[name]
    return ""


def _to_int(value: str) -> int:
    try:
        return max(0, int(float(value.replace(",", ""))))
    except (AttributeError, ValueError):
        return 0


def _split_values(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip().lstrip("#@") for part in re.split(r"[|,;]\s*", value) if part.strip()]


def _choice(value: str, allowed: set[str], default: str):
    lowered = (value or "").strip().lower()
    return lowered if lowered in allowed else default


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip().replace("Z", "+00:00")
    for candidate in (cleaned, cleaned.replace("/", "-")):
        try:
            dt = datetime.fromisoformat(candidate)
            return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
        except ValueError:
            pass
    return None
