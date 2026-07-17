from datetime import UTC, datetime

from app.analytics.engagement import compute_engagement_metrics
from app.providers.base import ProviderPost


def _p(pid, likes=0, replies=0, reposts=0, quotes=0, media="none", when=None):
    return ProviderPost(
        post_id=pid, text="x",
        created_at=when or datetime(2026, 1, 1, 12, tzinfo=UTC),
        like_count=likes, reply_count=replies, repost_count=reposts,
        quote_count=quotes, media_type=media,
    )


def test_empty():
    m = compute_engagement_metrics([])
    assert m["available"] is False
    assert m["total_engagement"] == 0


def test_averages_medians_totals():
    posts = [_p("1", likes=10, replies=2), _p("2", likes=20, replies=4), _p("3", likes=30, replies=6)]
    m = compute_engagement_metrics(posts)
    assert m["averages"]["likes"] == 20.0
    assert m["medians"]["likes"] == 20.0
    assert m["totals"]["likes"] == 60
    # engagement per post = likes+replies+reposts+quotes
    assert m["total_engagement"] == (10 + 2) + (20 + 4) + (30 + 6)
    assert m["avg_engagement_per_post"] == round(m["total_engagement"] / 3, 2)


def test_engagement_rate_with_followers():
    posts = [_p("1", likes=100)]
    m = compute_engagement_metrics(posts, followers=1000)
    # avg engagement 100 / 1000 followers => 10%
    assert m["approx_engagement_rate"] == 10.0


def test_engagement_rate_none_without_followers():
    m = compute_engagement_metrics([_p("1", likes=5)])
    assert m["approx_engagement_rate"] is None


def test_top_posts_sorted():
    posts = [_p("low", likes=1), _p("high", likes=500), _p("mid", likes=50)]
    m = compute_engagement_metrics(posts)
    assert m["top_posts"][0]["post_id"] == "high"
    assert m["top_posts"][-1]["post_id"] == "low"


def test_by_content_type():
    posts = [_p("1", likes=100, media="video"), _p("2", likes=0, media="none"),
             _p("3", likes=10, media="none")]
    m = compute_engagement_metrics(posts)
    types = {t["type"]: t["avg_engagement"] for t in m["by_content_type"]}
    assert types["video"] == 100.0
    assert types["none"] == 5.0


def test_by_hour_timezone_aware():
    # 03:00 UTC -> 08:00 Asia/Karachi
    post = _p("1", likes=10, when=datetime(2026, 3, 1, 3, tzinfo=UTC))
    m = compute_engagement_metrics([post], tz_name="Asia/Karachi")
    assert m["by_hour"][8] == 10.0
    assert m["by_hour"][3] == 0.0


def test_time_window_note_present():
    m = compute_engagement_metrics([_p("1", likes=1)])
    assert "accumulat" in m["time_window_note"].lower()
