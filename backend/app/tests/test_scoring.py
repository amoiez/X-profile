"""Unit tests for every automation-pattern scoring rule."""

from datetime import UTC, datetime, timedelta

from app.analytics.scoring import (
    DISCLAIMER,
    ScoringConfig,
    _score_continuous,
    _score_duplicate,
    _score_frequency,
    _score_regularity,
    _score_repeated_links,
    _score_reply_repost,
    compute_pattern_score,
)
from app.providers.base import ProviderPost

CFG = ScoringConfig()


def _posts_with_gaps(minutes: float, count: int) -> list[ProviderPost]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        ProviderPost(post_id=str(i), text="x", created_at=base + timedelta(minutes=minutes * i))
        for i in range(count)
    ]


# --- frequency ---
def test_frequency_zero_below_low():
    c = _score_frequency({"posts_per_day": CFG.freq_low - 1}, CFG)
    assert c["points"] == 0.0


def test_frequency_full_at_high():
    c = _score_frequency({"posts_per_day": CFG.freq_high}, CFG)
    assert c["points"] == CFG.max_frequency


def test_frequency_midpoint_half():
    mid = (CFG.freq_low + CFG.freq_high) / 2
    c = _score_frequency({"posts_per_day": mid}, CFG)
    assert abs(c["points"] - CFG.max_frequency / 2) < 0.01


# --- regularity ---
def test_regularity_full_for_constant_gaps():
    posts = _posts_with_gaps(60, 12)  # perfectly regular => CV 0
    c = _score_regularity(posts, CFG)
    assert c["points"] == CFG.max_regularity


def test_regularity_zero_when_too_few_posts():
    posts = _posts_with_gaps(60, 2)
    c = _score_regularity(posts, CFG)
    assert c["points"] == 0.0


def test_regularity_lower_for_irregular_gaps():
    base = datetime(2026, 1, 1, tzinfo=UTC)
    offsets = [0, 5, 400, 405, 1200, 1205, 3000]  # highly variable
    posts = [ProviderPost(post_id=str(i), text="x",
                          created_at=base + timedelta(minutes=o)) for i, o in enumerate(offsets)]
    c = _score_regularity(posts, CFG)
    assert c["points"] < CFG.max_regularity


# --- duplicate ---
def test_duplicate_zero():
    c = _score_duplicate({"duplicate_ratio": 0.0}, CFG)
    assert c["points"] == 0.0


def test_duplicate_full_at_threshold():
    c = _score_duplicate({"duplicate_ratio": CFG.duplicate_full_ratio}, CFG)
    assert c["points"] == CFG.max_duplicate


def test_duplicate_caps_above_threshold():
    c = _score_duplicate({"duplicate_ratio": 0.95}, CFG)
    assert c["points"] == CFG.max_duplicate


# --- continuous ---
def test_continuous_full_when_all_day_all_hours():
    activity = {"active_day_ratio": 1.0, "hourly_distribution": [1] * 24}
    c = _score_continuous(activity, CFG)
    assert c["points"] == CFG.max_continuous


def test_continuous_zero_when_inactive():
    activity = {"active_day_ratio": 0.0, "hourly_distribution": [0] * 24}
    c = _score_continuous(activity, CFG)
    assert c["points"] == 0.0


# --- repeated links / hashtags ---
def test_repeated_links_concentration():
    content = {"post_count": 10, "top_domains": [{"domain": "x.com", "count": 5}],
               "top_hashtags": []}
    c = _score_repeated_links(content, CFG)
    # 50% concentration == full at concentration_full_ratio 0.5
    assert c["points"] == CFG.max_repeated_links


def test_repeated_links_zero_without_repetition():
    content = {"post_count": 10, "top_domains": [], "top_hashtags": []}
    c = _score_repeated_links(content, CFG)
    assert c["points"] == 0.0


# --- reply/repost ---
def test_reply_repost_zero_below_low():
    activity = {"post_count": 10, "composition": {"repost": 1}}  # 10%
    c = _score_reply_repost(activity, CFG)
    assert c["points"] == 0.0


def test_reply_repost_full_at_high():
    activity = {"post_count": 10, "composition": {"repost": 7}}  # 70%
    c = _score_reply_repost(activity, CFG)
    assert c["points"] == CFG.max_reply_repost


# --- aggregate ---
def test_score_bounds_and_disclaimer():
    activity = {"posts_per_day": 0.0, "active_day_ratio": 0.0,
                "hourly_distribution": [0] * 24, "post_count": 3,
                "composition": {"repost": 0}}
    out = compute_pattern_score(posts=_posts_with_gaps(600, 3), activity=activity, content={})
    assert 0 <= out["automation_pattern_score"] <= 100
    assert out["disclaimer"] == DISCLAIMER
    assert len(out["components"]) == 6


def test_botlike_scores_higher_than_human():
    bot_posts = _posts_with_gaps(60, 30)
    bot_activity = {"posts_per_day": 48.0, "active_day_ratio": 1.0,
                    "hourly_distribution": [2] * 24, "post_count": 30,
                    "composition": {"repost": 20}}
    bot_content = {"post_count": 30, "duplicate_ratio": 0.6,
                   "top_domains": [{"domain": "x.com", "count": 20}], "top_hashtags": []}
    bot = compute_pattern_score(posts=bot_posts, activity=bot_activity, content=bot_content)

    human_posts = [ProviderPost(post_id=str(i), text="x",
                   created_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i * 7 + (i % 3)))
                   for i in range(12)]
    human_activity = {"posts_per_day": 3.0, "active_day_ratio": 0.4,
                      "hourly_distribution": [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 0, 0,
                                              0, 1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0],
                      "post_count": 12, "composition": {"repost": 1}}
    human_content = {"post_count": 12, "duplicate_ratio": 0.0, "top_domains": [], "top_hashtags": []}
    human = compute_pattern_score(posts=human_posts, activity=human_activity, content=human_content)

    assert bot["automation_pattern_score"] > human["automation_pattern_score"]
    assert bot["automation_pattern_score"] >= 70


def test_custom_config_changes_score():
    activity = {"posts_per_day": 10.0, "active_day_ratio": 0.0,
                "hourly_distribution": [0] * 24, "post_count": 5, "composition": {"repost": 0}}
    default = compute_pattern_score(posts=_posts_with_gaps(600, 5), activity=activity, content={})
    strict = compute_pattern_score(posts=_posts_with_gaps(600, 5), activity=activity, content={},
                                   config=ScoringConfig(freq_low=8, freq_high=12))
    assert strict["automation_pattern_score"] >= default["automation_pattern_score"]
