"""Admin monitoring endpoints (require admin role)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.database.session import get_session
from app.models import AnalysisJob, User
from app.models.analysis_job import JobStatus

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def stats(
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> dict:
    counts: dict[str, int] = {}
    for st in JobStatus:
        n = (
            await session.execute(
                select(func.count())
                .select_from(AnalysisJob)
                .where(AnalysisJob.status == st.value)
            )
        ).scalar_one()
        counts[st.value] = int(n)

    total_users = (
        await session.execute(select(func.count()).select_from(User))
    ).scalar_one()

    # Average processing time (seconds) for completed jobs.
    completed = (
        await session.execute(
            select(AnalysisJob.started_at, AnalysisJob.completed_at).where(
                AnalysisJob.status == JobStatus.COMPLETED.value
            )
        )
    ).all()
    durations = [
        (c - s).total_seconds()
        for s, c in completed
        if s is not None and c is not None
    ]
    avg_seconds = round(sum(durations) / len(durations), 3) if durations else None

    return {
        "jobs_by_status": counts,
        "total_jobs": sum(counts.values()),
        "failed_jobs": counts.get(JobStatus.FAILED.value, 0),
        "total_users": int(total_users),
        "avg_processing_seconds": avg_seconds,
    }
