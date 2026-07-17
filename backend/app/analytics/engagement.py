"""Engagement analysis.

Averages/medians/totals of likes, replies, reposts, quotes; per-post
engagement; approximate engagement rate (only when follower count is known);
top-performing posts; performance by content type, weekday, and posting hour
(timezone-aware).

A time-window limitation note is always included because recent posts have had
less time to accumulate engagement than older ones.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.providers.base import ProviderPost


def _resolve_tz(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        return ZoneInfo("UTC")


def _engagement(p: ProviderPost) -> int:
    return (p.like_count or 0) + (p.reply_count or 0) + (p.repost_count or 0) + (p.quote_count or 0)


def compute_engagement_metrics(
    posts: list[ProviderPost],
    followers: int | None = None,
    tz_name: str = "UTC",
) -> dict:
    n = len(posts)
    if n == 0:
        return {
            "available": False,
            "post_count": 0,
            "averages": {"likes": 0.0, "replies": 0.0, "reposts": 0.0, "quotes": 0.0},
            "medians": {"likes": 0.0, "replies": 0.0, "reposts": 0.0, "quotes": 0.0},
            "totals": {"likes": 0, "replies": 0, "reposts": 0, "quotes": 0},
            "total_engagement": 0,
            "avg_engagement_per_post": 0.0,
            "median_engagement": 0.0,
            "approx_engagement_rate": None,
            "top_posts": [],
            "by_content_type": [],
            "by_weekday": [0.0] * 7,
            "by_hour": [0.0] * 24,
            "time_window_note": _WINDOW_NOTE,
        }

    tz = _resolve_tz(tz_name)
    likes = [p.like_count or 0 for p in posts]
    replies = [p.reply_count or 0 for p in posts]
    reposts = [p.repost_count or 0 for p in posts]
    quotes = [p.quote_count or 0 for p in posts]
    eng = [_engagement(p) for p in posts]

    def _avg(xs):
        return round(statistics.mean(xs), 2)

    def _med(xs):
        return round(statistics.median(xs), 2)

    avg_eng = statistics.mean(eng)
    rate = None
    if followers and followers > 0:
        rate = round(100.0 * avg_eng / followers, 4)

    # Top posts by engagement.
    ranked = sorted(posts, key=_engagement, reverse=True)[:5]
    top_posts = [
        {
            "post_id": p.post_id,
            "text": (p.text or "")[:140],
            "created_at": p.created_at.isoformat(),
            "engagement": _engagement(p),
            "likes": p.like_count or 0,
            "replies": p.reply_count or 0,
            "reposts": p.repost_count or 0,
            "quotes": p.quote_count or 0,
            "media_type": p.media_type,
        }
        for p in ranked
    ]

    # By content type.
    type_eng: dict[str, list[int]] = {}
    for p, e in zip(posts, eng):
        type_eng.setdefault(p.media_type, []).append(e)
    by_content_type = sorted(
        (
            {"type": t, "avg_engagement": round(statistics.mean(v), 2), "count": len(v)}
            for t, v in type_eng.items()
        ),
        key=lambda x: x["avg_engagement"],
        reverse=True,
    )

    # By weekday / hour (timezone-aware average engagement).
    wd_sum = [0.0] * 7
    wd_cnt = [0] * 7
    hr_sum = [0.0] * 24
    hr_cnt = [0] * 24
    for p, e in zip(posts, eng):
        dt = p.created_at if p.created_at.tzinfo else p.created_at.replace(tzinfo=timezone.utc)
        lt = dt.astimezone(tz)
        wd_sum[lt.weekday()] += e
        wd_cnt[lt.weekday()] += 1
        hr_sum[lt.hour] += e
        hr_cnt[lt.hour] += 1
    by_weekday = [round(wd_sum[i] / wd_cnt[i], 2) if wd_cnt[i] else 0.0 for i in range(7)]
    by_hour = [round(hr_sum[i] / hr_cnt[i], 2) if hr_cnt[i] else 0.0 for i in range(24)]

    return {
        "available": True,
        "post_count": n,
        "averages": {
            "likes": _avg(likes),
            "replies": _avg(replies),
            "reposts": _avg(reposts),
            "quotes": _avg(quotes),
        },
        "medians": {
            "likes": _med(likes),
            "replies": _med(replies),
            "reposts": _med(reposts),
            "quotes": _med(quotes),
        },
        "totals": {
            "likes": sum(likes),
            "replies": sum(replies),
            "reposts": sum(reposts),
            "quotes": sum(quotes),
        },
        "total_engagement": sum(eng),
        "avg_engagement_per_post": round(avg_eng, 2),
        "median_engagement": round(statistics.median(eng), 2),
        "approx_engagement_rate": rate,
        "top_posts": top_posts,
        "by_content_type": by_content_type,
        "by_weekday": by_weekday,
        "by_hour": by_hour,
        "time_window_note": _WINDOW_NOTE,
    }


_WINDOW_NOTE = (
    "Engagement accumulates over time; recently published posts have had less "
    "time to gather likes, replies, and reposts than older posts. Compare "
    "posts within similar time windows."
)
