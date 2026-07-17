"""Database operations for analysis jobs and profiles.

Thin async data-access layer over SQLAlchemy. All queries go through the ORM
(parameterized) — no string-built SQL.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisJob, AnalysisResult, XProfile
from app.models.analysis_job import JobStatus
from app.providers.base import ProviderProfile


async def create_job(
    session: AsyncSession,
    *,
    username: str,
    post_limit: int,
    tz: str,
    user_id: str | None = None,
    data_source: str = "mock",
) -> AnalysisJob:
    job = AnalysisJob(
        username=username,
        requested_post_limit=post_limit,
        timezone=tz,
        user_id=user_id,
        data_source=data_source,
        status=JobStatus.PENDING.value,
        progress=0,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_job(session: AsyncSession, job_id: str) -> AnalysisJob | None:
    return await session.get(AnalysisJob, job_id)


async def get_result(session: AsyncSession, job_id: str) -> AnalysisResult | None:
    res = await session.execute(
        select(AnalysisResult).where(AnalysisResult.job_id == job_id)
    )
    return res.scalar_one_or_none()


async def list_jobs(
    session: AsyncSession,
    *,
    owner_id: str | None = None,
    only_unowned: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AnalysisJob], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    base = select(AnalysisJob)
    count_q = select(func.count()).select_from(AnalysisJob)
    if owner_id is not None:
        base = base.where(AnalysisJob.user_id == owner_id)
        count_q = count_q.where(AnalysisJob.user_id == owner_id)
    elif only_unowned:
        base = base.where(AnalysisJob.user_id.is_(None))
        count_q = count_q.where(AnalysisJob.user_id.is_(None))

    total = (await session.execute(count_q)).scalar_one()
    rows = (
        await session.execute(
            base.order_by(AnalysisJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return list(rows), int(total)


async def delete_job(session: AsyncSession, job_id: str) -> bool:
    job = await session.get(AnalysisJob, job_id)
    if job is None:
        return False
    await session.execute(delete(AnalysisJob).where(AnalysisJob.id == job_id))
    await session.commit()
    return True


async def update_progress(
    session: AsyncSession, job_id: str, *, stage: str, progress: int
) -> None:
    job = await session.get(AnalysisJob, job_id)
    if job is None:
        return
    job.current_stage = stage
    job.progress = progress
    if job.status == JobStatus.PENDING.value:
        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.now(UTC)
    await session.commit()


async def mark_failed(
    session: AsyncSession, job_id: str, *, code: str, message: str
) -> None:
    job = await session.get(AnalysisJob, job_id)
    if job is None:
        return
    job.status = JobStatus.FAILED.value
    job.error_code = code
    job.error_message = message[:512]
    job.completed_at = datetime.now(UTC)
    await session.commit()


async def upsert_profile(
    session: AsyncSession, profile: ProviderProfile
) -> XProfile:
    res = await session.execute(
        select(XProfile).where(XProfile.username == profile.username)
    )
    row = res.scalar_one_or_none()
    now = datetime.now(UTC)
    if row is None:
        row = XProfile(
            platform_user_id=profile.platform_user_id,
            username=profile.username,
            display_name=profile.display_name,
            public_profile_data=profile.to_public_dict(),
            last_retrieved_at=now,
        )
        session.add(row)
    else:
        row.platform_user_id = profile.platform_user_id
        row.display_name = profile.display_name
        row.public_profile_data = profile.to_public_dict()
        row.last_retrieved_at = now
    await session.commit()
    await session.refresh(row)
    return row
