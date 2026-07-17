"""Analysis job endpoints (API v1)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.database.session import get_session
from app.models.analysis_job import JobStatus
from app.schemas.analysis import (
    AnalysisCreateRequest,
    JobSummary,
    PaginatedJobs,
    ProgressResponse,
    ResultsResponse,
)
from app.services import job_service, queue, report_service

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    payload: AnalysisCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> JobSummary:
    from app.core.config import settings

    data_source = "mock" if settings.use_mock_provider else "x_api"
    job = await job_service.create_job(
        session,
        username=payload.username,
        post_limit=payload.post_limit,
        tz=payload.timezone,
        data_source=data_source,
    )
    await queue.enqueue(job.id)
    return JobSummary.model_validate(job)


@router.get("/{job_id}", response_model=JobSummary)
async def get_analysis(
    job_id: str, session: AsyncSession = Depends(get_session)
) -> JobSummary:
    job = await job_service.get_job(session, job_id)
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
    return JobSummary.model_validate(job)


@router.get("/{job_id}/progress", response_model=ProgressResponse)
async def get_progress(
    job_id: str, session: AsyncSession = Depends(get_session)
) -> ProgressResponse:
    job = await job_service.get_job(session, job_id)
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
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
    job_id: str, session: AsyncSession = Depends(get_session)
) -> ResultsResponse:
    job = await job_service.get_job(session, job_id)
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
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
) -> PaginatedJobs:
    rows, total = await job_service.list_jobs(session, page=page, page_size=page_size)
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
) -> FileResponse:
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
    job_id: str, session: AsyncSession = Depends(get_session)
) -> Response:
    ok = await job_service.delete_job(session, job_id)
    if not ok:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{job_id}/refresh", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
async def refresh_analysis(
    job_id: str, session: AsyncSession = Depends(get_session)
) -> JobSummary:
    old = await job_service.get_job(session, job_id)
    if old is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
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
