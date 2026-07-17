"""Transparent, deterministic automation-pattern scoring.

Produces a 0-100 "Possible Automation Pattern Score" from six independently
computed, capped components. Every component returns its points, its maximum,
and a plain-language explanation of the observable signal that drove it. There
is no black-box: the sum of the components IS the score.

The thresholds live in ``ScoringConfig`` and are documented and configurable.
Each rule is unit-tested.

IMPORTANT: the score describes observable posting patterns only. It is NOT
proof that an account is automated or operated by a bot.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from app import METHODOLOGY_VERSION
from app.providers.base import ProviderPost

DISCLAIMER = (
    "This score represents observable posting patterns and is not proof that "
    "the account is automated or operated by a bot."
)


@dataclass(frozen=True)
class ScoringConfig:
    # Component maximums (sum = 100).
    max_frequency: int = 20
    max_regularity: int = 20
    max_duplicate: int = 20
    max_continuous: int = 15
    max_repeated_links: int = 15
    max_reply_repost: int = 10

    # Posting frequency (posts/day): below low => 0, at/above high => full.
    freq_low: float = 5.0
    freq_high: float = 50.0

    # Interval regularity: coefficient of variation of inter-post gaps.
    # At/below cv_low => full (very regular); at/above cv_high => 0.
    cv_low: float = 0.15
    cv_high: float = 1.0
    regularity_min_posts: int = 5

    # Duplicate content ratio at which the duplicate component is full.
    duplicate_full_ratio: float = 0.5

    # Repeated link/hashtag concentration at which the component is full.
    concentration_full_ratio: float = 0.5

    # Reply/repost concentration: repost fraction below `repost_low` => 0,
    # at/above `repost_high` => full.
    repost_low: float = 0.2
    repost_high: float = 0.7


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _component(key, label, points, max_points, explanation, signals=None) -> dict:
    return {
        "key": key,
        "label": label,
        "points": round(points, 2),
        "max_points": max_points,
        "explanation": explanation,
        "signals": signals or {},
    }


def _score_frequency(activity: dict, cfg: ScoringConfig) -> dict:
    ppd = activity.get("posts_per_day") or 0.0
    ratio = _clamp01((ppd - cfg.freq_low) / (cfg.freq_high - cfg.freq_low))
    pts = ratio * cfg.max_frequency
    return _component(
        "posting_frequency", "Posting frequency", pts, cfg.max_frequency,
        f"Average of {ppd:g} posts/day. Higher sustained frequency raises this "
        f"component (0 at ≤{cfg.freq_low:g}/day, full at ≥{cfg.freq_high:g}/day).",
        {"posts_per_day": ppd},
    )


def _score_regularity(posts: list[ProviderPost], cfg: ScoringConfig) -> dict:
    times = sorted(_as_utc(p.created_at) for p in posts)
    gaps = [
        (times[i] - times[i - 1]).total_seconds() / 60.0 for i in range(1, len(times))
    ]
    if len(gaps) < cfg.regularity_min_posts - 1 or not gaps:
        return _component(
            "regular_intervals", "Regular posting intervals", 0.0, cfg.max_regularity,
            "Not enough posts to assess interval regularity.",
            {"gap_count": len(gaps)},
        )
    mean_gap = statistics.mean(gaps)
    if mean_gap <= 0:
        cv = 0.0
    else:
        cv = statistics.pstdev(gaps) / mean_gap
    # Low CV (very regular) => high score.
    regularity = _clamp01((cfg.cv_high - cv) / (cfg.cv_high - cfg.cv_low))
    pts = regularity * cfg.max_regularity
    return _component(
        "regular_intervals", "Regular posting intervals", pts, cfg.max_regularity,
        f"Coefficient of variation of gaps between posts is {cv:.2f}. Very "
        f"regular spacing (low variation) raises this component.",
        {"gap_cv": round(cv, 3), "median_gap_minutes": round(statistics.median(gaps), 2)},
    )


def _score_duplicate(content: dict | None, cfg: ScoringConfig) -> dict:
    ratio = (content or {}).get("duplicate_ratio", 0.0) or 0.0
    pts = _clamp01(ratio / cfg.duplicate_full_ratio) * cfg.max_duplicate
    return _component(
        "duplicate_content", "Duplicate content", pts, cfg.max_duplicate,
        f"About {ratio * 100:.0f}% of posts are duplicate or near-duplicate. "
        f"Full at ≥{cfg.duplicate_full_ratio * 100:.0f}%.",
        {"duplicate_ratio": ratio},
    )


def _score_continuous(activity: dict, cfg: ScoringConfig) -> dict:
    active_ratio = activity.get("active_day_ratio", 0.0) or 0.0
    hourly = activity.get("hourly_distribution", [0] * 24)
    active_hours = sum(1 for h in hourly if h > 0)
    hour_coverage = active_hours / 24.0
    pts = (active_ratio * 0.5 + hour_coverage * 0.5) * cfg.max_continuous
    return _component(
        "continuous_daily_activity", "Continuous daily activity", pts, cfg.max_continuous,
        f"Active on {active_ratio * 100:.0f}% of days in range and across "
        f"{active_hours}/24 hours of the day. Round-the-clock, every-day activity "
        "raises this component.",
        {"active_day_ratio": active_ratio, "active_hours": active_hours},
    )


def _score_repeated_links(content: dict | None, cfg: ScoringConfig) -> dict:
    content = content or {}
    n = content.get("post_count", 0) or 0
    top_domain = content.get("top_domains") or []
    top_hashtag = content.get("top_hashtags") or []
    domain_conc = (top_domain[0]["count"] / n) if (n and top_domain) else 0.0
    hashtag_conc = (top_hashtag[0]["count"] / n) if (n and top_hashtag) else 0.0
    concentration = max(domain_conc, hashtag_conc)
    pts = _clamp01(concentration / cfg.concentration_full_ratio) * cfg.max_repeated_links
    return _component(
        "repeated_links_hashtags", "Repeated links & hashtags", pts, cfg.max_repeated_links,
        f"Most-shared domain/hashtag appears in {concentration * 100:.0f}% of posts. "
        f"Highly concentrated repetition raises this component.",
        {"domain_concentration": round(domain_conc, 3),
         "hashtag_concentration": round(hashtag_conc, 3)},
    )


def _score_reply_repost(activity: dict, cfg: ScoringConfig) -> dict:
    comp = activity.get("composition", {})
    n = activity.get("post_count", 0) or 0
    reposts = comp.get("repost", 0)
    repost_ratio = (reposts / n) if n else 0.0
    ratio = _clamp01((repost_ratio - cfg.repost_low) / (cfg.repost_high - cfg.repost_low))
    pts = ratio * cfg.max_reply_repost
    return _component(
        "reply_repost_concentration", "Reply/repost concentration", pts, cfg.max_reply_repost,
        f"Reposts make up {repost_ratio * 100:.0f}% of posts. An unusually high "
        "repost share raises this component.",
        {"repost_ratio": round(repost_ratio, 3)},
    )


def compute_pattern_score(
    *,
    posts: list[ProviderPost],
    activity: dict,
    content: dict | None,
    config: ScoringConfig | None = None,
) -> dict:
    cfg = config or ScoringConfig()
    components = [
        _score_frequency(activity, cfg),
        _score_regularity(posts, cfg),
        _score_duplicate(content, cfg),
        _score_continuous(activity, cfg),
        _score_repeated_links(content, cfg),
        _score_reply_repost(activity, cfg),
    ]
    total = sum(c["points"] for c in components)
    score = int(round(max(0.0, min(100.0, total))))

    # Signals that contributed meaningfully (>= 40% of their max).
    signals_triggered = [
        c["label"] for c in components if c["max_points"] and c["points"] >= 0.4 * c["max_points"]
    ]

    return {
        "automation_pattern_score": score,
        "disclaimer": DISCLAIMER,
        "components": components,
        "signals_triggered": signals_triggered,
        "config": asdict(cfg),
        "methodology_version": METHODOLOGY_VERSION,
    }
