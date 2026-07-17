"""Pattern indicators + automation-pattern score.

Surfaces the individual observable signals (each as a plain fact) and attaches
the transparent score from ``scoring``. Signals are descriptive, not
conclusive.
"""

from __future__ import annotations

from app.analytics.scoring import DISCLAIMER, ScoringConfig, compute_pattern_score
from app.providers.base import ProviderPost


def compute_pattern_metrics(
    *,
    posts: list[ProviderPost],
    activity: dict,
    content: dict | None = None,
    config: ScoringConfig | None = None,
) -> dict:
    scored = compute_pattern_score(
        posts=posts, activity=activity, content=content, config=config
    )

    indicators = _build_indicators(activity, content or {})

    return {
        **scored,
        "indicators": indicators,
        "disclaimer": DISCLAIMER,
    }


def _build_indicators(activity: dict, content: dict) -> list[dict]:
    """Human-readable observable signals with their measured values."""
    n = activity.get("post_count", 0) or 0
    hourly = activity.get("hourly_distribution", [0] * 24)
    active_hours = sum(1 for h in hourly if h > 0)
    comp = activity.get("composition", {})
    repost_ratio = (comp.get("repost", 0) / n) if n else 0.0
    reply_ratio = (comp.get("reply", 0) / n) if n else 0.0
    top_domain = (content.get("top_domains") or [{}])[0] if content.get("top_domains") else {}
    top_hashtag = (content.get("top_hashtags") or [{}])[0] if content.get("top_hashtags") else {}

    def ind(key, present, label, value):
        return {"key": key, "present": bool(present), "label": label, "value": value}

    return [
        ind("high_frequency", (activity.get("posts_per_day") or 0) >= 20,
            "Very high posting frequency", activity.get("posts_per_day")),
        ind("regular_intervals",
            (activity.get("daily_count_cv") is not None and activity.get("daily_count_cv") < 0.3),
            "Regular posting intervals", activity.get("daily_count_cv")),
        ind("round_the_clock", active_hours >= 20,
            "Posts at nearly every hour of the day", active_hours),
        ind("duplicate_posts", (content.get("duplicate_ratio") or 0) > 0.1,
            "Duplicate or near-duplicate posts", content.get("duplicate_ratio")),
        ind("repeated_links", (top_domain.get("count", 0) / n if n else 0) > 0.3,
            "Repeated links / concentrated domain sharing", top_domain.get("domain")),
        ind("repeated_hashtags", (top_hashtag.get("count", 0) / n if n else 0) > 0.3,
            "Repeated hashtags", top_hashtag.get("tag")),
        ind("high_repost_ratio", repost_ratio > 0.5,
            "Unusually high repost ratio", round(repost_ratio, 3)),
        ind("high_reply_ratio", reply_ratio > 0.7,
            "Unusually high reply ratio", round(reply_ratio, 3)),
        ind("posting_bursts", (activity.get("burst_count") or 0) > 0,
            "Short posting bursts", activity.get("burst_count")),
        ind("long_continuous_window", (activity.get("active_day_ratio") or 0) >= 0.9,
            "Long continuous activity window", activity.get("active_day_ratio")),
    ]
