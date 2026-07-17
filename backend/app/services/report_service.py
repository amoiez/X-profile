"""Report generation service: assemble analysis data and render a PDF."""

from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.models import AnalysisJob, Report, XProfile
from app.models.analysis_job import JobStatus
from app.reports.pdf import generate_report_pdf
from app.services import job_service


def _to_summary_dict(job: AnalysisJob) -> dict:
    return {
        "id": job.id,
        "username": job.username,
        "status": job.status,
        "data_source": job.data_source,
        "actual_post_count": job.actual_post_count,
    }


async def build_report_payload(session: AsyncSession, job: AnalysisJob) -> dict:
    result = await job_service.get_result(session, job.id)
    if result is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)

    profile: dict = {}
    if job.profile_id:
        prof = await session.get(XProfile, job.profile_id)
        if prof:
            profile = prof.public_profile_data

    return {
        "job": _to_summary_dict(job),
        "profile": profile,
        "activity_metrics": result.activity_metrics,
        "content_metrics": result.content_metrics,
        "sentiment_metrics": result.sentiment_metrics,
        "engagement_metrics": result.engagement_metrics,
        "pattern_metrics": result.pattern_metrics,
        "summary": result.summary,
        "data_quality": result.data_quality,
    }


async def generate_pdf_for_job(
    session: AsyncSession, job_id: str, *, force: bool = False
) -> str:
    job = await job_service.get_job(session, job_id)
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, http_status=404)
    if job.status != JobStatus.COMPLETED.value:
        raise AppError(
            ErrorCode.ANALYSIS_FAILED,
            "A report can only be generated for a completed analysis.",
            http_status=409,
        )

    storage_dir = settings.report_storage_path
    os.makedirs(storage_dir, exist_ok=True)
    output_path = os.path.join(storage_dir, f"{job_id}.pdf")

    if force or not os.path.exists(output_path):
        payload = await build_report_payload(session, job)
        generate_report_pdf(payload, output_path)
        await _record_report(session, job_id, output_path)

    return output_path


async def _record_report(session: AsyncSession, job_id: str, path: str) -> None:
    existing = (
        await session.execute(select(Report).where(Report.job_id == job_id))
    ).scalar_one_or_none()
    if existing is None:
        session.add(Report(job_id=job_id, format="pdf", storage_path=path))
    else:
        existing.storage_path = path
    await session.commit()
