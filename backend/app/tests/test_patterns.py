from datetime import datetime, timedelta, timezone

from app.analytics.activity import compute_activity_metrics
from app.analytics.content import compute_content_metrics
from app.analytics.patterns import compute_pattern_metrics
from app.providers.base import ProviderPost


def _bot_posts(n=40):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        ProviderPost(
            post_id=str(i),
            text="Check our latest deal https://shop.example.io/x #sale",
            created_at=base + timedelta(minutes=30 * i),
            hashtags=["sale"], urls=["https://shop.example.io/x"],
            post_type="repost" if i % 2 else "original", media_type="link",
        )
        for i in range(n)
    ]


def test_pattern_metrics_structure():
    posts = _bot_posts(40)
    activity = compute_activity_metrics(posts, "UTC")
    content = compute_content_metrics(posts)
    m = compute_pattern_metrics(posts=posts, activity=activity, content=content)
    assert "automation_pattern_score" in m
    assert "disclaimer" in m
    assert "not proof" in m["disclaimer"].lower()
    assert len(m["components"]) == 6
    assert len(m["indicators"]) == 10
    assert all("present" in ind for ind in m["indicators"])


def test_botlike_high_score_and_signals():
    posts = _bot_posts(48)
    activity = compute_activity_metrics(posts, "UTC")
    content = compute_content_metrics(posts)
    m = compute_pattern_metrics(posts=posts, activity=activity, content=content)
    assert m["automation_pattern_score"] >= 60
    # duplicate + repeated links signals should be present
    keys = {i["key"] for i in m["indicators"] if i["present"]}
    assert "duplicate_posts" in keys
    assert "repeated_links" in keys


def test_low_activity_low_score():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    posts = [
        ProviderPost(post_id=str(i), text=f"unique human thought number {i} about life",
                     created_at=base + timedelta(days=i * 2, hours=(i * 5) % 12 + 9))
        for i in range(8)
    ]
    activity = compute_activity_metrics(posts, "UTC")
    content = compute_content_metrics(posts)
    m = compute_pattern_metrics(posts=posts, activity=activity, content=content)
    assert m["automation_pattern_score"] < 40
