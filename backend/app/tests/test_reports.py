"""PDF report generation test."""

from __future__ import annotations

import os

from app.reports.pdf import generate_report_pdf


def _sample_payload() -> dict:
    return {
        "job": {"username": "sample_user", "data_source": "mock"},
        "profile": {
            "username": "sample_user", "display_name": "Sample User",
            "verified": True, "created_at": "2020-01-01T00:00:00+00:00",
            "followers_count": 12345, "following_count": 321, "tweet_count": 9999,
        },
        "activity_metrics": {
            "post_count": 50, "posts_per_day": 3.2, "posts_per_week": 22.4,
            "median_minutes_between_posts": 180.0, "timezone": "UTC",
            "most_active_hour": {"hour": 14, "count": 8},
            "most_active_weekday": {"name": "Tuesday", "count": 12},
            "composition": {"original": 30, "reply": 12, "repost": 6, "quote": 2},
            "weekly_distribution": [5, 12, 8, 7, 9, 4, 5], "burst_count": 1,
            "longest_inactive_hours": 20.5,
        },
        "content_metrics": {
            "avg_post_length": 142.0, "duplicate_ratio": 0.12,
            "top_keywords": [{"term": "python", "count": 10}, {"term": "data", "count": 8}],
            "top_hashtags": [{"tag": "tech", "count": 5}],
            "top_mentions": [{"username": "alice", "count": 3}],
            "top_domains": [{"domain": "example.com", "count": 4}],
            "dominant_topics": [{"topic": "technology", "weight": 0.4}],
        },
        "sentiment_metrics": {
            "available": True, "model": "vader", "analyzed_count": 50,
            "skipped_unsupported": 0, "average_compound": 0.21,
            "distribution": {"positive": 40.0, "neutral": 50.0, "negative": 10.0},
            "limitations": ["Sarcasm is not reliably detected."],
        },
        "engagement_metrics": {
            "available": True, "avg_engagement_per_post": 123.4, "median_engagement": 80,
            "averages": {"likes": 90, "replies": 12, "reposts": 20},
            "approx_engagement_rate": 1.2, "total_engagement": 6170,
            "time_window_note": "Engagement accumulates over time.",
        },
        "pattern_metrics": {
            "automation_pattern_score": 72,
            "disclaimer": "This score represents observable posting patterns and is not proof "
                          "that the account is automated or operated by a bot.",
            "components": [
                {"label": "Posting frequency", "points": 12.0, "max_points": 20},
                {"label": "Duplicate content", "points": 5.0, "max_points": 20},
            ],
            "indicators": [{"label": "Duplicate or near-duplicate posts", "present": True}],
        },
        "summary": {
            "headline": "Within the analyzed sample of 50 posts, the account shows...",
            "findings": ["The collected posts indicate frequent activity.",
                         "The account appears most active on Tuesdays."],
        },
        "data_quality": {
            "post_count": 50, "earliest_post": "2026-01-01T00:00:00+00:00",
            "latest_post": "2026-02-01T00:00:00+00:00", "detected_language": "en",
            "methodology_version": "1.0.0", "is_mock": True, "low_confidence": False,
            "generated_at": "2026-07-18T00:00:00+00:00",
        },
    }


def test_generate_pdf_creates_valid_file(tmp_path):
    out = str(tmp_path / "report.pdf")
    result = generate_report_pdf(_sample_payload(), out)
    assert result == out
    assert os.path.exists(out)
    assert os.path.getsize(out) > 1000  # non-trivial PDF
    with open(out, "rb") as f:
        assert f.read(5) == b"%PDF-"


def test_generate_pdf_handles_low_confidence_and_unavailable(tmp_path):
    payload = _sample_payload()
    payload["data_quality"]["low_confidence"] = True
    payload["data_quality"]["post_count"] = 4
    payload["sentiment_metrics"] = {"available": False, "reason": "unsupported_language",
                                    "limitations": []}
    payload["engagement_metrics"] = {"available": False}
    out = str(tmp_path / "low.pdf")
    generate_report_pdf(payload, out)
    assert os.path.getsize(out) > 1000
