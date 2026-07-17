from datetime import datetime, timedelta, timezone

from app.analytics.sentiment import compute_sentiment_metrics
from app.providers.base import ProviderPost


def _p(text, lang="en", pid="1", when=None, hashtags=None):
    return ProviderPost(
        post_id=pid, text=text, lang=lang,
        created_at=when or datetime(2026, 1, 1, tzinfo=timezone.utc),
        hashtags=hashtags or [],
    )


def test_positive_negative_neutral_classification():
    posts = [
        _p("I love this, it is wonderful and amazing!", pid="1"),
        _p("This is terrible, awful and I hate it.", pid="2"),
        _p("The meeting is at 3pm on Tuesday.", pid="3"),
        _p("What a fantastic, brilliant day!", pid="4"),
        _p("Absolutely horrible experience, very disappointing.", pid="5"),
    ]
    m = compute_sentiment_metrics(posts)
    assert m["available"] is True
    assert m["counts"]["positive"] >= 2
    assert m["counts"]["negative"] >= 2
    assert round(sum(m["distribution"].values())) == 100


def test_unsupported_language_returns_unavailable():
    posts = [_p("bonjour le monde ceci est un texte", lang="fr", pid=str(i)) for i in range(5)]
    m = compute_sentiment_metrics(posts)
    assert m["available"] is False
    assert m["reason"] == "unsupported_language"
    assert m["skipped_unsupported"] == 5


def test_insufficient_posts_unavailable():
    posts = [_p("good", pid="1")]
    m = compute_sentiment_metrics(posts)
    assert m["available"] is False


def test_deterministic():
    posts = [_p("I really love sunny mornings and good coffee", pid=str(i)) for i in range(6)]
    a = compute_sentiment_metrics(posts)
    b = compute_sentiment_metrics(posts)
    assert a["average_compound"] == b["average_compound"]


def test_trend_by_day():
    d0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    posts = [
        _p("great day", pid="1", when=d0),
        _p("awful day", pid="2", when=d0),
        _p("nice one", pid="3", when=d0 + timedelta(days=1)),
        _p("bad one", pid="4", when=d0 + timedelta(days=1)),
    ]
    m = compute_sentiment_metrics(posts)
    assert len(m["trend"]) == 2
    assert m["trend"][0]["date"] == "2026-01-01"


def test_limitations_mention_sarcasm():
    posts = [_p("good", pid=str(i)) for i in range(5)]
    m = compute_sentiment_metrics(posts)
    assert any("sarcasm" in lim.lower() for lim in m["limitations"])
