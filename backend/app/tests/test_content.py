from datetime import datetime, timezone

from app.analytics.content import compute_content_metrics
from app.providers.base import ProviderPost


def _p(text, pid="1", hashtags=None, mentions=None, urls=None, media="none"):
    return ProviderPost(
        post_id=pid, text=text, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        hashtags=hashtags or [], mentions=mentions or [], urls=urls or [], media_type=media,
    )


def test_empty():
    m = compute_content_metrics([])
    assert m["post_count"] == 0
    assert m["top_keywords"] == []
    assert m["unique_ratio"] == 1.0


def test_keyword_extraction_removes_noise():
    posts = [
        _p("The python data pipeline is amazing https://example.com @friend #tech",
           mentions=["friend"], hashtags=["tech"], urls=["https://example.com/a"]),
        _p("python python data science rocks"),
    ]
    m = compute_content_metrics(posts)
    terms = {k["term"] for k in m["top_keywords"]}
    assert "python" in terms and "data" in terms
    # stopwords, url host, and mention removed
    assert "the" not in terms
    assert "friend" not in terms
    assert "example" not in terms


def test_hashtags_mentions_domains():
    posts = [
        _p("post one", hashtags=["AI", "Tech"], mentions=["alice"],
           urls=["https://news.example.org/x"]),
        _p("post two", hashtags=["ai"], mentions=["alice", "bob"],
           urls=["http://www.news.example.org/y"]),
    ]
    m = compute_content_metrics(posts)
    tags = {h["tag"]: h["count"] for h in m["top_hashtags"]}
    assert tags["ai"] == 2  # case-normalized
    mentions = {x["username"]: x["count"] for x in m["top_mentions"]}
    assert mentions["alice"] == 2
    domains = {d["domain"]: d["count"] for d in m["top_domains"]}
    assert domains["news.example.org"] == 2  # www stripped


def test_duplicate_detection_and_ratio():
    posts = [
        _p("Buy now at our shop!", pid="1"),
        _p("Buy now at our shop!", pid="2"),
        _p("Buy now at our shop!", pid="3"),
        _p("A totally different message", pid="4"),
    ]
    m = compute_content_metrics(posts)
    assert m["duplicate_groups"][0]["count"] == 3
    # 3 identical => 2 redundant of 4 posts => 0.5
    assert m["duplicate_ratio"] == 0.5
    assert m["unique_ratio"] == 0.5


def test_media_usage_percentages():
    posts = [_p("a", media="image"), _p("b", media="image"),
             _p("c", media="video"), _p("d", media="none")]
    m = compute_content_metrics(posts)
    assert m["media_usage"]["image"] == 2
    assert m["media_usage"]["percentages"]["image"] == 50.0


def test_avg_length():
    posts = [_p("12345"), _p("1234567890")]
    m = compute_content_metrics(posts)
    assert m["avg_post_length"] == 7.5
