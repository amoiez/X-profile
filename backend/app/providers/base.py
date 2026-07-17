"""Provider interface and normalized domain models.

Every provider (mock or real) returns the same normalized `ProviderProfile`
and `ProviderPost` shapes so the analytics engine is provider-agnostic.
Fields that may be absent for a given API access level are Optional and must
be handled safely downstream.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class ProviderProfile:
    """Normalized public profile."""

    platform_user_id: str
    username: str
    display_name: str | None = None
    bio: str | None = None
    created_at: datetime | None = None
    verified: bool = False
    protected: bool = False
    followers_count: int | None = None
    following_count: int | None = None
    tweet_count: int | None = None
    listed_count: int | None = None
    profile_image_url: str | None = None

    def to_public_dict(self) -> dict:
        return {
            "platform_user_id": self.platform_user_id,
            "username": self.username,
            "display_name": self.display_name,
            "bio": self.bio,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "verified": self.verified,
            "protected": self.protected,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "tweet_count": self.tweet_count,
            "listed_count": self.listed_count,
            "profile_image_url": self.profile_image_url,
        }


PostType = Literal["original", "reply", "repost", "quote"]
MediaType = Literal["none", "image", "video", "gif", "poll", "link"]


@dataclass(frozen=True)
class ProviderPost:
    """Normalized public post."""

    post_id: str
    text: str
    created_at: datetime
    lang: str | None = None
    post_type: PostType = "original"
    media_type: MediaType = "none"
    like_count: int = 0
    reply_count: int = 0
    repost_count: int = 0
    quote_count: int = 0
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    conversation_id: str | None = None
    in_reply_to_user_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "post_id": self.post_id,
            "text": self.text,
            "created_at": self.created_at.isoformat(),
            "lang": self.lang,
            "post_type": self.post_type,
            "media_type": self.media_type,
            "like_count": self.like_count,
            "reply_count": self.reply_count,
            "repost_count": self.repost_count,
            "quote_count": self.quote_count,
            "hashtags": self.hashtags,
            "mentions": self.mentions,
            "urls": self.urls,
            "conversation_id": self.conversation_id,
            "in_reply_to_user_id": self.in_reply_to_user_id,
        }


@dataclass
class RateLimitStatus:
    limit: int | None = None
    remaining: int | None = None
    reset_at: datetime | None = None


class BaseXProvider(abc.ABC):
    """Abstract data provider."""

    #: "mock" or "x_api" — surfaced to the UI/report for transparency.
    name: str = "base"

    @abc.abstractmethod
    async def get_user_by_username(self, username: str) -> ProviderProfile:
        """Return the public profile or raise a mapped ProviderError."""

    @abc.abstractmethod
    async def get_user_posts(
        self, profile: ProviderProfile, limit: int
    ) -> list[ProviderPost]:
        """Return up to `limit` recent public posts, newest first."""

    @abc.abstractmethod
    async def get_rate_limit_status(self) -> RateLimitStatus:
        """Return current rate-limit status if known."""

    async def aclose(self) -> None:  # pragma: no cover - default no-op
        """Release any held resources (HTTP clients, etc.)."""
        return None
