"""Posting-activity analytics.

Pure functions over a list of ``ProviderPost``. Timezone-aware: hour/weekday
distributions are computed in the report timezone (default UTC), while
interval-based metrics use absolute UTC deltas.

Implemented with the standard library (no pandas) so the scored logic stays
portable and trivially unit-testable.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.providers.base import ProviderPost

_WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


@dataclass(frozen=True)
class ActivityConfig:
    #: minimum posts within `burst_window_minutes` to count as a burst
    burst_min_posts: int = 5
    burst_window_minutes: int = 60


def _resolve_tz(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        return ZoneInfo("UTC")


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_activity_metrics(
    posts: list[ProviderPost],
    tz_name: str = "UTC",
    config: ActivityConfig | None = None,
) -> dict:
    """Compute posting-activity metrics. Empty input yields a zeroed, safe dict."""
    config = config or ActivityConfig()
    tz = _resolve_tz(tz_name)

    hourly = [0] * 24
    weekly = [0] * 7
    composition = {"original": 0, "reply": 0, "repost": 0, "quote": 0}

    if not posts:
        return {
            "post_count": 0,
            "timezone": tz_name,
            "posts_per_day": 0.0,
            "posts_per_week": 0.0,
            "median_minutes_between_posts": None,
            "most_active_weekday": None,
            "most_active_hour": None,
            "hourly_distribution": hourly,
            "weekly_distribution": weekly,
            "composition": {**composition, "percentages": {k: 0.0 for k in composition}},
            "active_day_ratio": 0.0,
            "daily_count_cv": None,
            "longest_inactive_hours": None,
            "bursts": [],
            "burst_count": 0,
            "span_days": 0.0,
            "first_post_at": None,
            "last_post_at": None,
        }

    # Sort ascending by absolute time.
    ordered = sorted(posts, key=lambda p: _as_utc(p.created_at))
    utc_times = [_as_utc(p.created_at) for p in ordered]
    local_times = [t.astimezone(tz) for t in utc_times]

    for lt in local_times:
        hourly[lt.hour] += 1
        weekly[lt.weekday()] += 1

    for p in ordered:
        if p.post_type in composition:
            composition[p.post_type] += 1

    first_utc, last_utc = utc_times[0], utc_times[-1]
    span_seconds = (last_utc - first_utc).total_seconds()
    span_days = span_seconds / 86400.0
    n = len(ordered)

    # Rates: guard against zero/near-zero spans (all posts same instant).
    effective_days = max(span_days, 1.0 / 24)  # at least one hour
    posts_per_day = n / effective_days if span_days > 0 else float(n)
    posts_per_week = posts_per_day * 7

    # Intervals between consecutive posts (minutes).
    gaps_minutes = [
        (utc_times[i] - utc_times[i - 1]).total_seconds() / 60.0
        for i in range(1, n)
    ]
    median_gap = statistics.median(gaps_minutes) if gaps_minutes else None
    longest_inactive_hours = (max(gaps_minutes) / 60.0) if gaps_minutes else None

    # Most active weekday / hour.
    max_wd = max(range(7), key=lambda i: weekly[i])
    max_hr = max(range(24), key=lambda i: hourly[i])
    most_active_weekday = (
        {"index": max_wd, "name": _WEEKDAY_NAMES[max_wd], "count": weekly[max_wd]}
        if weekly[max_wd] > 0
        else None
    )
    most_active_hour = (
        {"hour": max_hr, "count": hourly[max_hr]} if hourly[max_hr] > 0 else None
    )

    # Daily counts (in local tz) for consistency metrics.
    per_day: dict[str, int] = {}
    for lt in local_times:
        key = lt.date().isoformat()
        per_day[key] = per_day.get(key, 0) + 1
    active_days = len(per_day)
    total_days = max(1, int(span_days) + 1)
    active_day_ratio = min(1.0, active_days / total_days)
    daily_counts = list(per_day.values())
    daily_count_cv = (
        (statistics.pstdev(daily_counts) / statistics.mean(daily_counts))
        if len(daily_counts) > 1 and statistics.mean(daily_counts) > 0
        else None
    )

    bursts = _detect_bursts(utc_times, ordered, config)

    pct = {k: round(100.0 * v / n, 2) for k, v in composition.items()}

    return {
        "post_count": n,
        "timezone": tz_name,
        "posts_per_day": round(posts_per_day, 3),
        "posts_per_week": round(posts_per_week, 3),
        "median_minutes_between_posts": round(median_gap, 2) if median_gap is not None else None,
        "most_active_weekday": most_active_weekday,
        "most_active_hour": most_active_hour,
        "hourly_distribution": hourly,
        "weekly_distribution": weekly,
        "composition": {**composition, "percentages": pct},
        "active_day_ratio": round(active_day_ratio, 3),
        "daily_count_cv": round(daily_count_cv, 3) if daily_count_cv is not None else None,
        "longest_inactive_hours": round(longest_inactive_hours, 2)
        if longest_inactive_hours is not None
        else None,
        "bursts": bursts,
        "burst_count": len(bursts),
        "span_days": round(span_days, 3),
        "first_post_at": first_utc.isoformat(),
        "last_post_at": last_utc.isoformat(),
    }


def _detect_bursts(
    utc_times: list[datetime],
    ordered: list[ProviderPost],
    config: ActivityConfig,
) -> list[dict]:
    """Sliding-window burst detection: >= burst_min_posts within the window.

    Returns non-overlapping bursts (advance past a detected burst's end).
    """
    window = config.burst_window_minutes * 60
    n = len(utc_times)
    bursts: list[dict] = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and (utc_times[j + 1] - utc_times[i]).total_seconds() <= window:
            j += 1
        count = j - i + 1
        if count >= config.burst_min_posts:
            bursts.append(
                {
                    "start": utc_times[i].isoformat(),
                    "end": utc_times[j].isoformat(),
                    "count": count,
                }
            )
            i = j + 1  # skip past this burst
        else:
            i += 1
    return bursts
