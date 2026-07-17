"""Content analysis.

Keyword, hashtag, mention, domain, topic, media, length, repeated-phrase, and
duplicate/near-duplicate metrics. URLs, mentions, hashtags, punctuation, and
stop words are removed before keyword extraction.

Implemented with the standard library so results are deterministic and easily
tested. (spaCy / scikit-learn could enhance topic modeling later; the engine
interface would not change.)
"""

from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlparse

from app.providers.base import ProviderPost

# Compact English stop-word list (extend as needed).
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "when", "at",
    "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "of", "is",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "doing", "this", "that", "these", "those", "i", "you", "he",
    "she", "it", "we", "they", "them", "his", "her", "its", "our", "their",
    "my", "your", "me", "us", "am", "as", "so", "no", "not", "just", "now",
    "will", "can", "would", "should", "could", "get", "got", "im", "dont",
    "rt", "amp", "via", "one", "like", "today", "new", "more", "here",
}

_URL_RE = re.compile(r"https?://\S+|\b\w+\.\w{2,}(?:/\S*)?")
_MENTION_RE = re.compile(r"@\w+")
_HASHTAG_RE = re.compile(r"#\w+")
_TOKEN_RE = re.compile(r"[a-z][a-z']+")

_TOPIC_LEXICON = {
    "technology": {"ai", "python", "cloud", "data", "software", "code", "coding",
                   "tech", "startup", "opensource", "devops", "app", "developer"},
    "news_politics": {"breaking", "report", "policy", "government", "election",
                      "world", "economy", "market", "update"},
    "sports": {"football", "match", "score", "team", "season", "goal", "game",
               "playoffs", "league", "player"},
    "lifestyle": {"coffee", "travel", "food", "fitness", "music", "weekend",
                  "morning", "life", "photo"},
    "business": {"business", "sales", "growth", "revenue", "product", "launch",
                 "customers", "marketing", "deal"},
}


def _clean_for_keywords(text: str) -> list[str]:
    lowered = text.lower()
    lowered = _URL_RE.sub(" ", lowered)
    lowered = _MENTION_RE.sub(" ", lowered)
    lowered = _HASHTAG_RE.sub(" ", lowered)
    tokens = _TOKEN_RE.findall(lowered)
    return [t for t in tokens if len(t) >= 3 and t not in STOP_WORDS]


def _domain_of(url: str) -> str | None:
    if not url:
        return None
    candidate = url if "://" in url else f"http://{url}"
    try:
        netloc = urlparse(candidate).netloc.lower()
    except ValueError:
        return None
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc or None


def _normalize_dup(text: str) -> str:
    lowered = text.lower()
    lowered = _URL_RE.sub("", lowered)
    lowered = _MENTION_RE.sub("", lowered)
    lowered = re.sub(r"[^a-z0-9 ]", "", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def compute_content_metrics(posts: list[ProviderPost]) -> dict:
    n = len(posts)
    media_types = ["none", "image", "video", "gif", "poll", "link"]
    media_counts = dict.fromkeys(media_types, 0)

    if n == 0:
        return {
            "post_count": 0,
            "top_keywords": [],
            "top_hashtags": [],
            "top_mentions": [],
            "top_domains": [],
            "dominant_topics": [],
            "media_usage": {**media_counts, "percentages": {k: 0.0 for k in media_types}},
            "avg_post_length": 0.0,
            "avg_word_count": 0.0,
            "repeated_phrases": [],
            "duplicate_groups": [],
            "duplicate_ratio": 0.0,
            "unique_ratio": 1.0,
        }

    keyword_counter: Counter[str] = Counter()
    hashtag_counter: Counter[str] = Counter()
    mention_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    bigram_counter: Counter[str] = Counter()
    trigram_counter: Counter[str] = Counter()
    dup_counter: Counter[str] = Counter()

    total_chars = 0
    total_words = 0

    for p in posts:
        total_chars += len(p.text or "")
        tokens = _clean_for_keywords(p.text or "")
        total_words += len(tokens)
        keyword_counter.update(tokens)

        for i in range(len(tokens) - 1):
            bigram_counter[f"{tokens[i]} {tokens[i + 1]}"] += 1
        for i in range(len(tokens) - 2):
            trigram_counter[f"{tokens[i]} {tokens[i + 1]} {tokens[i + 2]}"] += 1

        hashtag_counter.update(h.lower() for h in (p.hashtags or []))
        mention_counter.update(m.lower() for m in (p.mentions or []))
        for u in (p.urls or []):
            d = _domain_of(u)
            if d:
                domain_counter[d] += 1

        if p.media_type in media_counts:
            media_counts[p.media_type] += 1

        dup_counter[_normalize_dup(p.text or "")] += 1

    # Duplicate/near-duplicate groups (normalized-exact).
    duplicate_groups = [
        {"text": t[:120], "count": c}
        for t, c in dup_counter.most_common()
        if c > 1 and t  # ignore empty-normalized
    ]
    redundant = sum(g["count"] - 1 for g in duplicate_groups)
    duplicate_ratio = round(redundant / n, 3)

    repeated_phrases = [
        {"phrase": ph, "count": c}
        for ph, c in (trigram_counter + bigram_counter).most_common(10)
        if c >= 3
    ]

    dominant_topics = _dominant_topics(keyword_counter, hashtag_counter)

    pct = {k: round(100.0 * v / n, 2) for k, v in media_counts.items()}

    return {
        "post_count": n,
        "top_keywords": [{"term": t, "count": c} for t, c in keyword_counter.most_common(20)],
        "top_hashtags": [{"tag": t, "count": c} for t, c in hashtag_counter.most_common(15)],
        "top_mentions": [{"username": t, "count": c} for t, c in mention_counter.most_common(15)],
        "top_domains": [{"domain": t, "count": c} for t, c in domain_counter.most_common(15)],
        "dominant_topics": dominant_topics,
        "media_usage": {**media_counts, "percentages": pct},
        "avg_post_length": round(total_chars / n, 1),
        "avg_word_count": round(total_words / n, 2),
        "repeated_phrases": repeated_phrases,
        "duplicate_groups": duplicate_groups[:15],
        "duplicate_ratio": duplicate_ratio,
        "unique_ratio": round(1.0 - duplicate_ratio, 3),
    }


def _dominant_topics(keywords: Counter, hashtags: Counter) -> list[dict]:
    """Score topics by summed frequency of their lexicon terms among keywords/hashtags."""
    combined: Counter[str] = Counter()
    combined.update(keywords)
    combined.update({k: v for k, v in hashtags.items()})
    scores: list[dict] = []
    total = sum(combined.values()) or 1
    for topic, terms in _TOPIC_LEXICON.items():
        matched = {t: combined[t] for t in terms if combined.get(t)}
        weight = sum(matched.values())
        if weight:
            scores.append(
                {
                    "topic": topic,
                    "weight": round(weight / total, 3),
                    "terms": [t for t, _ in Counter(matched).most_common(5)],
                }
            )
    scores.sort(key=lambda s: s["weight"], reverse=True)
    return scores
