"""Deterministic mock X provider.

Produces realistic, reproducible profiles and posts seeded from the username
so tests and demos are stable. Reserved usernames trigger specific error
states so the full UX (protected, not-found, suspended, empty) can be
exercised without real API access.

All output is clearly labeled as demonstration data via `name = "mock"`.
"""

from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime, timedelta

from app.core.errors import (
    ProfileNotFoundError,
    ProfileProtectedError,
    ProfileSuspendedError,
)
from app.providers.base import (
    BaseXProvider,
    MediaType,
    PostType,
    ProviderPost,
    ProviderProfile,
    RateLimitStatus,
)

# Reserved usernames for deterministic error-state demos/tests.
RESERVED: dict[str, str] = {
    "notfound_demo": "not_found",
    "protected_demo": "protected",
    "suspended_demo": "suspended",
    "empty_demo": "empty",
}
SHOWCASE_USERNAMES = {"news_bot", "sample_user", "coffee_lover"}
DEMO_USERNAMES = tuple(sorted(set(RESERVED) | SHOWCASE_USERNAMES))

# Topic vocab used to synthesize believable content.
_TOPICS = {
    "tech": ["ai", "python", "cloud", "data", "opensource", "startup", "coding", "devops"],
    "news": ["breaking", "update", "report", "world", "market", "policy", "economy"],
    "sports": ["football", "match", "score", "team", "season", "goal", "playoffs"],
    "lifestyle": ["coffee", "travel", "food", "fitness", "morning", "weekend", "music"],
}
_DOMAINS = ["example.com", "news.example.org", "blog.example.net", "shop.example.io"]
_MENTIONS = ["teammate", "official", "friend_acct", "newsdesk", "devrel"]


def _seed_for(username: str) -> int:
    # Normalize so "@name" and "name" seed identically.
    normalized = username.lstrip("@").lower()
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return int(digest[:12], 16)


def is_demo_username(username: str) -> bool:
    return username.lstrip("@").lower() in set(DEMO_USERNAMES)


class MockXProvider(BaseXProvider):
    name = "mock"

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime.now(UTC)

    async def get_user_by_username(self, username: str) -> ProviderProfile:
        key = username.lower()
        if key in RESERVED:
            kind = RESERVED[key]
            if kind == "not_found":
                raise ProfileNotFoundError()
            if kind == "protected":
                # Return a protected profile so callers can decide messaging.
                raise ProfileProtectedError()
            if kind == "suspended":
                raise ProfileSuspendedError()
            # "empty" falls through to a normal profile with zero posts.

        rng = random.Random(_seed_for(username))
        followers = rng.randint(50, 500_000)
        following = rng.randint(20, 5_000)
        created = self._now - timedelta(days=rng.randint(120, 4_500))
        return ProviderProfile(
            platform_user_id=str(_seed_for(username)),
            username=username.lstrip("@"),
            display_name=username.lstrip("@").replace("_", " ").title(),
            bio=rng.choice(
                [
                    "Sharing thoughts on technology and the world.",
                    "Coffee, code, and occasional hot takes.",
                    "News, analysis, and updates. Opinions my own.",
                    "Building things on the internet.",
                ]
            ),
            created_at=created,
            verified=rng.random() < 0.15,
            protected=False,
            followers_count=followers,
            following_count=following,
            tweet_count=rng.randint(200, 40_000),
            listed_count=rng.randint(0, 500),
            profile_image_url="https://abs.twimg.com/sticky/default_profile_images/default_profile.png",
        )

    async def get_user_posts(
        self, profile: ProviderProfile, limit: int
    ) -> list[ProviderPost]:
        if profile.username.lower() == "empty_demo":
            return []

        rng = random.Random(_seed_for(profile.username) ^ 0xA5A5)

        # Decide an archetype so different usernames look different.
        # "botlike" archetype => very regular intervals, duplicates, many links.
        botlike = "bot" in profile.username.lower() or rng.random() < 0.2
        topic_name = rng.choice(list(_TOPICS.keys()))
        topic_words = _TOPICS[topic_name]

        n = min(limit, rng.randint(0, 3) + rng.randint(40, 260))
        if profile.username.lower() == "empty_demo":
            n = 0

        posts: list[ProviderPost] = []
        cursor = self._now

        # Interval model: bot => near-constant; human => variable, day/night.
        base_interval_min = 60 if botlike else rng.randint(90, 600)

        duplicate_pool = [
            f"Check out our latest {topic_name} update! https://{rng.choice(_DOMAINS)}/a",
            f"New post is live. Read more: https://{rng.choice(_DOMAINS)}/b",
        ]

        for i in range(n):
            if botlike:
                gap = base_interval_min + rng.randint(-3, 3)
            else:
                # Humans post less at night (UTC hours 0-6 heuristic).
                gap = base_interval_min + rng.randint(-40, 240)
                if 0 <= cursor.hour < 6:
                    gap += rng.randint(120, 480)
            cursor = cursor - timedelta(minutes=max(5, gap))

            post_type = self._pick_post_type(rng, botlike)
            media_type, urls = self._pick_media(rng, botlike)
            hashtags = rng.sample(topic_words, k=min(2, rng.randint(0, 3)))
            mentions = (
                rng.sample(_MENTIONS, k=1) if rng.random() < (0.5 if post_type == "reply" else 0.15) else []
            )

            if botlike and rng.random() < 0.35:
                text = rng.choice(duplicate_pool)
                if not urls:
                    urls = [text.split("https://")[-1]]
            else:
                text = self._make_text(rng, topic_words, hashtags, mentions, urls)

            posts.append(
                ProviderPost(
                    post_id=f"{profile.platform_user_id}-{i}",
                    text=text,
                    created_at=cursor,
                    lang="en",
                    post_type=post_type,
                    media_type=media_type,
                    like_count=self._metric(rng, followers=profile.followers_count, k=0.02),
                    reply_count=self._metric(rng, followers=profile.followers_count, k=0.004),
                    repost_count=self._metric(rng, followers=profile.followers_count, k=0.008),
                    quote_count=self._metric(rng, followers=profile.followers_count, k=0.002),
                    hashtags=hashtags,
                    mentions=mentions,
                    urls=urls,
                    conversation_id=f"conv-{i // 5}",
                    in_reply_to_user_id="12345" if post_type == "reply" else None,
                )
            )

        return posts

    async def get_rate_limit_status(self) -> RateLimitStatus:
        return RateLimitStatus(limit=1_000_000, remaining=1_000_000, reset_at=None)

    # --- helpers ---
    @staticmethod
    def _pick_post_type(rng: random.Random, botlike: bool) -> PostType:
        r = rng.random()
        if botlike:
            # bots skew original/repost
            return "original" if r < 0.7 else ("repost" if r < 0.9 else "reply")
        if r < 0.55:
            return "original"
        if r < 0.8:
            return "reply"
        if r < 0.93:
            return "repost"
        return "quote"

    @staticmethod
    def _pick_media(rng: random.Random, botlike: bool) -> tuple[MediaType, list[str]]:
        r = rng.random()
        if botlike and r < 0.6:
            d = rng.choice(_DOMAINS)
            return "link", [f"{d}/article"]
        if r < 0.45:
            return "none", []
        if r < 0.65:
            d = rng.choice(_DOMAINS)
            return "link", [f"{d}/page"]
        if r < 0.85:
            return "image", []
        if r < 0.95:
            return "video", []
        return "poll", []

    @staticmethod
    def _make_text(
        rng: random.Random,
        topic_words: list[str],
        hashtags: list[str],
        mentions: list[str],
        urls: list[str],
    ) -> str:
        openers = [
            "Really enjoying",
            "Thinking about",
            "Here is my take on",
            "Quick thought:",
            "Big news about",
            "Just tried",
        ]
        subj = rng.choice(topic_words)
        parts = [f"{rng.choice(openers)} {subj} today."]
        if mentions:
            parts.append(" ".join(f"@{m}" for m in mentions))
        if hashtags:
            parts.append(" ".join(f"#{h}" for h in hashtags))
        if urls:
            parts.append(f"https://{urls[0]}")
        return " ".join(parts)

    @staticmethod
    def _metric(rng: random.Random, followers: int | None, k: float) -> int:
        base = (followers or 1000) * k
        # log-normal-ish spread; occasional viral post
        val = rng.gauss(base, base * 0.7)
        if rng.random() < 0.03:
            val *= rng.uniform(5, 30)
        return max(0, int(abs(val)))
