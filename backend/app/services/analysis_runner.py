"""Analysis pipeline runner.

Executes an analysis job end to end: retrieve profile + posts via the
configured provider, run the analytics engines, build the summary and
data-quality block, and persist results. Progress and stage are written to the
job row at each step so the UI can poll them.

Milestone 2 implements the activity engine. Content/sentiment/engagement/
pattern engines are called through optional imports and slot in during
Milestone 3 without changing this orchestration.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app import METHODOLOGY_VERSION
from app.analytics.activity import compute_activity_metrics
from app.analytics.content import compute_content_metrics
from app.analytics.engagement import compute_engagement_metrics
from app.analytics.patterns import compute_pattern_metrics
from app.analytics.sentiment import compute_sentiment_metrics
from app.analytics.summarizer import build_summary
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.database.session import AsyncSessionLocal
from app.models import AnalysisResult
from app.models.analysis_job import JobStatus
from app.providers import get_provider
from app.providers.base import ProviderPost
from app.services import job_service
from app.services.stages import (
    STAGE_ACTIVITY,
    STAGE_CONTENT,
    STAGE_DONE,
    STAGE_ENGAGEMENT,
    STAGE_PATTERNS,
    STAGE_PROGRESS,
    STAGE_RETRIEVING_POSTS,
    STAGE_RETRIEVING_PROFILE,
    STAGE_SENTIMENT,
    STAGE_SUMMARY,
    STAGE_VALIDATING,
)

logger = get_logger("runner")


async def run_job(job_id: str) -> None:
    """Run a job by id using its own DB session. Safe to call from a worker."""
    async with AsyncSessionLocal() as session:
        job = await job_service.get_job(session, job_id)
        if job is None:
            logger.warning("run_job_missing", job_id=job_id)
            return
        if job.status in (JobStatus.COMPLETED.value, JobStatus.RUNNING.value):
            logger.info("run_job_skip", job_id=job_id, status=job.status)
            return

        provider = get_provider()
        try:
            await job_service.update_progress(
                session, job_id, stage=STAGE_VALIDATING,
                progress=STAGE_PROGRESS[STAGE_VALIDATING],
            )

            # --- profile ---
            await job_service.update_progress(
                session, job_id, stage=STAGE_RETRIEVING_PROFILE,
                progress=STAGE_PROGRESS[STAGE_RETRIEVING_PROFILE],
            )
            profile = await provider.get_user_by_username(job.username)
            profile_row = await job_service.upsert_profile(session, profile)

            # reload job (progress updates expired attrs)
            job = await job_service.get_job(session, job_id)
            job.profile_id = profile_row.id
            job.data_source = provider.name
            await session.commit()

            # --- posts ---
            await job_service.update_progress(
                session, job_id, stage=STAGE_RETRIEVING_POSTS,
                progress=STAGE_PROGRESS[STAGE_RETRIEVING_POSTS],
            )
            posts: list[ProviderPost] = await provider.get_user_posts(
                profile, job.requested_post_limit
            )

            if not posts:
                raise AppError(
                    ErrorCode.NO_POSTS_AVAILABLE,
                    http_status=422,
                )

            job = await job_service.get_job(session, job_id)
            job.actual_post_count = len(posts)
            times = sorted(_as_utc(p.created_at) for p in posts)
            job.period_start = times[0]
            job.period_end = times[-1]
            await session.commit()

            # --- activity (Milestone 2) ---
            await job_service.update_progress(
                session, job_id, stage=STAGE_ACTIVITY,
                progress=STAGE_PROGRESS[STAGE_ACTIVITY],
            )
            tz_name = job.timezone
            activity = compute_activity_metrics(posts, tz_name=tz_name)

            # --- content (Milestone 3) ---
            await job_service.update_progress(
                session, job_id, stage=STAGE_CONTENT,
                progress=STAGE_PROGRESS[STAGE_CONTENT],
            )
            content = compute_content_metrics(posts)

            # --- sentiment (Milestone 3) ---
            await job_service.update_progress(
                session, job_id, stage=STAGE_SENTIMENT,
                progress=STAGE_PROGRESS[STAGE_SENTIMENT],
            )
            sentiment = compute_sentiment_metrics(posts)

            # --- engagement (Milestone 3) ---
            await job_service.update_progress(
                session, job_id, stage=STAGE_ENGAGEMENT,
                progress=STAGE_PROGRESS[STAGE_ENGAGEMENT],
            )
            engagement = compute_engagement_metrics(
                posts, followers=profile.followers_count, tz_name=tz_name
            )

            # --- patterns + score (Milestone 3) ---
            await job_service.update_progress(
                session, job_id, stage=STAGE_PATTERNS,
                progress=STAGE_PROGRESS[STAGE_PATTERNS],
            )
            patterns = compute_pattern_metrics(
                posts=posts, activity=activity, content=content
            )

            # --- summary + data quality ---
            await job_service.update_progress(
                session, job_id, stage=STAGE_SUMMARY,
                progress=STAGE_PROGRESS[STAGE_SUMMARY],
            )
            data_quality = _build_data_quality(profile, posts, activity, provider.name)
            summary = build_summary(
                profile=profile.to_public_dict(),
                activity=activity,
                content=content,
                sentiment=sentiment,
                engagement=engagement,
                patterns=patterns,
                data_quality=data_quality,
            )

            result = AnalysisResult(
                job_id=job_id,
                activity_metrics=activity,
                content_metrics=content or {},
                sentiment_metrics=sentiment or {},
                engagement_metrics=engagement or {},
                pattern_metrics=patterns or {},
                summary=summary,
                data_quality=data_quality,
                methodology_version=METHODOLOGY_VERSION,
            )
            session.add(result)

            job = await job_service.get_job(session, job_id)
            job.status = JobStatus.COMPLETED.value
            job.current_stage = STAGE_DONE
            job.progress = STAGE_PROGRESS[STAGE_DONE]
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info("run_job_done", job_id=job_id, posts=len(posts))

        except AppError as exc:
            await job_service.mark_failed(
                session, job_id, code=exc.code.value, message=exc.message
            )
            logger.info("run_job_failed", job_id=job_id, error_code=exc.code.value)
        except Exception as exc:  # noqa: BLE001
            await job_service.mark_failed(
                session, job_id,
                code=ErrorCode.ANALYSIS_FAILED.value,
                message="Analysis failed unexpectedly.",
            )
            logger.error("run_job_error", job_id=job_id, error=type(exc).__name__)
        finally:
            await provider.aclose()


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _build_data_quality(profile, posts, activity, data_source: str) -> dict:
    n = len(posts)
    langs: dict[str, int] = {}
    for p in posts:
        if p.lang:
            langs[p.lang] = langs.get(p.lang, 0) + 1
    detected = max(langs, key=langs.get) if langs else None
    return {
        "post_count": n,
        "earliest_post": activity.get("first_post_at"),
        "latest_post": activity.get("last_post_at"),
        "detected_language": detected,
        "language_distribution": langs,
        "methodology_version": METHODOLOGY_VERSION,
        "data_source": data_source,
        "is_mock": data_source == "mock",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "low_confidence": n < settings.low_confidence_post_threshold,
        "low_confidence_threshold": settings.low_confidence_post_threshold,
        "missing_metrics": [],
    }
