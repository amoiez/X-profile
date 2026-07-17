"""Sentiment analysis.

Language is detected first; the English VADER model is the baseline. Posts in
unsupported languages are skipped (not misclassified). If too few English posts
are available, sentiment is reported as unavailable rather than misleading.

VADER does not reliably detect sarcasm; this limitation is stated explicitly.
An optional multilingual Hugging Face model could be added later behind the
same interface.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import UTC

from langdetect import DetectorFactory, LangDetectException, detect
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.providers.base import ProviderPost

# Deterministic language detection.
DetectorFactory.seed = 0

SUPPORTED_LANGUAGES = {"en"}
POS_THRESHOLD = 0.05
NEG_THRESHOLD = -0.05
MIN_ANALYZABLE = 3

_analyzer = SentimentIntensityAnalyzer()
_URL_RE = re.compile(r"https?://\S+")


def _detect_lang(post: ProviderPost) -> str | None:
    if post.lang:
        return post.lang
    text = _URL_RE.sub("", post.text or "").strip()
    if len(text) < 3:
        return None
    try:
        return detect(text)
    except LangDetectException:
        return None


def _classify(compound: float) -> str:
    if compound >= POS_THRESHOLD:
        return "positive"
    if compound <= NEG_THRESHOLD:
        return "negative"
    return "neutral"


def compute_sentiment_metrics(posts: list[ProviderPost]) -> dict:
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    compounds: list[float] = []
    by_day: dict[str, list[float]] = defaultdict(list)
    by_hashtag: dict[str, list[float]] = defaultdict(list)
    lang_counter: dict[str, int] = defaultdict(int)
    skipped = 0

    for p in posts:
        lang = _detect_lang(p)
        if lang:
            lang_counter[lang] += 1
        if lang not in SUPPORTED_LANGUAGES:
            skipped += 1
            continue
        score = _analyzer.polarity_scores(_URL_RE.sub("", p.text or ""))["compound"]
        label = _classify(score)
        counts[label] += 1
        compounds.append(score)

        dt = p.created_at if p.created_at.tzinfo else p.created_at.replace(tzinfo=UTC)
        by_day[dt.astimezone(UTC).date().isoformat()].append(score)
        for h in (p.hashtags or []):
            by_hashtag[h.lower()].append(score)

    analyzed = len(compounds)
    detected_language = (
        max(lang_counter, key=lang_counter.get) if lang_counter else None
    )

    limitations = [
        "Sentiment is computed with the English VADER lexicon model.",
        "Sarcasm and irony are not reliably detected.",
        "Scores are approximate signals, not definitive judgments.",
    ]

    if analyzed < MIN_ANALYZABLE:
        return {
            "available": False,
            "reason": "unsupported_language"
            if posts and skipped >= len(posts)
            else "insufficient_english_posts",
            "model": "vader",
            "analyzed_count": analyzed,
            "skipped_unsupported": skipped,
            "detected_language": detected_language,
            "distribution": {"positive": 0.0, "neutral": 0.0, "negative": 0.0},
            "counts": counts,
            "average_compound": None,
            "trend": [],
            "by_hashtag": [],
            "limitations": limitations,
        }

    distribution = {
        k: round(100.0 * v / analyzed, 2) for k, v in counts.items()
    }
    trend = [
        {"date": day, "average": round(sum(v) / len(v), 4), "count": len(v)}
        for day, v in sorted(by_day.items())
    ]
    by_hashtag_out = sorted(
        (
            {"hashtag": h, "average": round(sum(v) / len(v), 4), "count": len(v)}
            for h, v in by_hashtag.items()
            if len(v) >= 2
        ),
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return {
        "available": True,
        "model": "vader",
        "analyzed_count": analyzed,
        "skipped_unsupported": skipped,
        "detected_language": detected_language,
        "distribution": distribution,
        "counts": counts,
        "average_compound": round(sum(compounds) / analyzed, 4),
        "trend": trend,
        "by_hashtag": by_hashtag_out,
        "confidence_note": (
            "Low confidence: small sample."
            if analyzed < 10
            else "Model-based approximation."
        ),
        "limitations": limitations,
    }
