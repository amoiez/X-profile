from datetime import UTC, datetime, timedelta

from app.analytics.activity import ActivityConfig, compute_activity_metrics
from app.providers.base import ProviderPost


def _post(dt: datetime, ptype: str = "original", pid: str = "x") -> ProviderPost:
    return ProviderPost(post_id=pid, text="hello", created_at=dt, post_type=ptype)


def test_empty_posts_returns_safe_zeroed_metrics():
    m = compute_activity_metrics([], tz_name="UTC")
    assert m["post_count"] == 0
    assert m["posts_per_day"] == 0.0
    assert m["most_active_hour"] is None
    assert m["hourly_distribution"] == [0] * 24
    assert m["bursts"] == []


def test_rates_and_span():
    base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    # 10 posts, one per day => ~1 post/day over 9 days span.
    posts = [_post(base + timedelta(days=i), pid=str(i)) for i in range(10)]
    m = compute_activity_metrics(posts, tz_name="UTC")
    assert m["post_count"] == 10
    assert m["span_days"] == 9.0
    assert round(m["posts_per_day"], 2) == round(10 / 9, 2)
    assert round(m["posts_per_week"], 2) == round(10 / 9 * 7, 2)


def test_median_interval_and_longest_gap():
    base = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    times = [base, base + timedelta(minutes=10), base + timedelta(minutes=20),
             base + timedelta(hours=5)]
    posts = [_post(t, pid=str(i)) for i, t in enumerate(times)]
    m = compute_activity_metrics(posts, tz_name="UTC")
    # gaps: 10, 10, 280 minutes -> median 10
    assert m["median_minutes_between_posts"] == 10.0
    assert m["longest_inactive_hours"] == round(280 / 60, 2)


def test_timezone_shifts_hour_distribution():
    # 03:00 UTC == 08:00 in Asia/Karachi (+5)
    dt = datetime(2026, 3, 10, 3, 0, tzinfo=UTC)
    posts = [_post(dt, pid="1")]
    utc = compute_activity_metrics(posts, tz_name="UTC")
    kar = compute_activity_metrics(posts, tz_name="Asia/Karachi")
    assert utc["most_active_hour"]["hour"] == 3
    assert kar["most_active_hour"]["hour"] == 8


def test_invalid_timezone_falls_back_to_utc():
    dt = datetime(2026, 3, 10, 3, 0, tzinfo=UTC)
    m = compute_activity_metrics([_post(dt)], tz_name="Not/AZone")
    assert m["most_active_hour"]["hour"] == 3


def test_composition_percentages():
    base = datetime(2026, 1, 1, tzinfo=UTC)
    posts = (
        [_post(base + timedelta(minutes=i), "original", str(i)) for i in range(6)]
        + [_post(base + timedelta(minutes=100 + i), "reply", "r%d" % i) for i in range(2)]
        + [_post(base + timedelta(minutes=200 + i), "repost", "t%d" % i) for i in range(2)]
    )
    m = compute_activity_metrics(posts, tz_name="UTC")
    c = m["composition"]
    assert c["original"] == 6 and c["reply"] == 2 and c["repost"] == 2
    assert c["percentages"]["original"] == 60.0


def test_burst_detection():
    base = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    # 6 posts within 10 minutes -> one burst (min 5 within 60m)
    burst_posts = [_post(base + timedelta(minutes=i * 2), pid=f"b{i}") for i in range(6)]
    # then a lone post much later
    later = [_post(base + timedelta(days=2), pid="late")]
    m = compute_activity_metrics(burst_posts + later, tz_name="UTC",
                                 config=ActivityConfig(burst_min_posts=5, burst_window_minutes=60))
    assert m["burst_count"] == 1
    assert m["bursts"][0]["count"] == 6


def test_no_burst_when_spread_out():
    base = datetime(2026, 1, 1, tzinfo=UTC)
    posts = [_post(base + timedelta(hours=i * 3), pid=str(i)) for i in range(6)]
    m = compute_activity_metrics(posts, tz_name="UTC")
    assert m["burst_count"] == 0


def test_single_post_no_gaps():
    m = compute_activity_metrics([_post(datetime(2026, 1, 1, tzinfo=UTC))], "UTC")
    assert m["post_count"] == 1
    assert m["median_minutes_between_posts"] is None
    assert m["longest_inactive_hours"] is None
    assert m["posts_per_day"] == 1.0
