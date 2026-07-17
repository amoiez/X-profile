"""Real X (Twitter) API v2 provider.

Uses environment-based credentials, timeouts, retries with exponential
backoff, respects HTTP 429 rate-limit reset headers, paginates safely up to
the requested post limit, maps provider errors to application error codes,
and never logs the bearer token.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.errors import (
    CredentialsMissingError,
    ErrorCode,
    ProfileNotFoundError,
    ProfileProtectedError,
    ProfileSuspendedError,
    ProviderError,
    RateLimitedError,
)
from app.core.logging import get_logger
from app.providers.base import (
    BaseXProvider,
    MediaType,
    PostType,
    ProviderPost,
    ProviderProfile,
    RateLimitStatus,
)

logger = get_logger("provider.x_api")

_USER_FIELDS = (
    "created_at,description,protected,verified,public_metrics,profile_image_url"
)
_TWEET_FIELDS = "created_at,lang,public_metrics,entities,referenced_tweets,in_reply_to_user_id,attachments,conversation_id"
_MAX_PAGE = 100  # X API v2 cap per page for user tweets timeline


class XApiProvider(BaseXProvider):
    name = "x_api"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        if not settings.x_api_bearer_token:
            raise CredentialsMissingError()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=settings.x_api_base_url,
            timeout=settings.x_request_timeout_seconds,
            headers={"Authorization": f"Bearer {settings.x_api_bearer_token}"},
        )
        self._last_rate_limit = RateLimitStatus()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # --- public API ---
    async def get_user_by_username(self, username: str) -> ProviderProfile:
        handle = username.lstrip("@")
        data = await self._request(
            "GET", f"/users/by/username/{handle}", params={"user.fields": _USER_FIELDS}
        )
        errors = data.get("errors")
        if errors and "data" not in data:
            title = (errors[0].get("title") or "").lower()
            if "suspended" in title:
                raise ProfileSuspendedError()
            raise ProfileNotFoundError()

        u = data.get("data")
        if not u:
            raise ProfileNotFoundError()

        if u.get("protected"):
            raise ProfileProtectedError()

        pm = u.get("public_metrics", {}) or {}
        return ProviderProfile(
            platform_user_id=str(u["id"]),
            username=u.get("username", handle),
            display_name=u.get("name"),
            bio=u.get("description"),
            created_at=_parse_dt(u.get("created_at")),
            verified=bool(u.get("verified", False)),
            protected=bool(u.get("protected", False)),
            followers_count=pm.get("followers_count"),
            following_count=pm.get("following_count"),
            tweet_count=pm.get("tweet_count"),
            listed_count=pm.get("listed_count"),
            profile_image_url=u.get("profile_image_url"),
        )

    async def get_user_posts(
        self, profile: ProviderProfile, limit: int
    ) -> list[ProviderPost]:
        limit = max(1, min(limit, settings.x_max_post_limit))
        collected: list[ProviderPost] = []
        pagination_token: str | None = None

        while len(collected) < limit:
            page_size = min(_MAX_PAGE, limit - len(collected))
            if page_size < 5:
                page_size = 5  # API minimum
            params = {
                "max_results": page_size,
                "tweet.fields": _TWEET_FIELDS,
                "exclude": "",  # keep replies/retweets so we can classify them
            }
            if pagination_token:
                params["pagination_token"] = pagination_token

            data = await self._request(
                "GET", f"/users/{profile.platform_user_id}/tweets", params=params
            )
            for raw in data.get("data", []) or []:
                collected.append(_map_tweet(raw))
                if len(collected) >= limit:
                    break

            meta = data.get("meta", {}) or {}
            pagination_token = meta.get("next_token")
            if not pagination_token:
                break

        return collected[:limit]

    async def get_rate_limit_status(self) -> RateLimitStatus:
        return self._last_rate_limit

    # --- internals ---
    async def _request(self, method: str, path: str, params: dict | None = None) -> dict:
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = await self._client.request(method, path, params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt <= settings.x_max_retries:
                    await asyncio.sleep(_backoff(attempt))
                    continue
                raise ProviderError(ErrorCode.NETWORK_ERROR) from exc

            self._capture_rate_limit(resp)

            if resp.status_code == 429:
                retry_after = _reset_seconds(resp)
                if attempt <= settings.x_max_retries and retry_after <= 5:
                    await asyncio.sleep(retry_after or _backoff(attempt))
                    continue
                raise RateLimitedError(retry_after=retry_after)

            if resp.status_code in (401, 403):
                # 403 can be protected; surfaced by caller via body inspection.
                if resp.status_code == 401:
                    raise CredentialsMissingError()
                raise ProfileProtectedError()

            if resp.status_code == 404:
                raise ProfileNotFoundError()

            if resp.status_code >= 500:
                if attempt <= settings.x_max_retries:
                    await asyncio.sleep(_backoff(attempt))
                    continue
                raise ProviderError(ErrorCode.PROVIDER_ERROR, http_status=502)

            if resp.status_code >= 400:
                logger.warning("provider_client_error", status=resp.status_code)
                raise ProviderError(ErrorCode.PROVIDER_ERROR)

            return resp.json()

    def _capture_rate_limit(self, resp: httpx.Response) -> None:
        try:
            self._last_rate_limit = RateLimitStatus(
                limit=int(resp.headers.get("x-rate-limit-limit", 0)) or None,
                remaining=int(resp.headers.get("x-rate-limit-remaining", 0)) or None,
                reset_at=(
                    datetime.fromtimestamp(
                        int(resp.headers["x-rate-limit-reset"]), tz=timezone.utc
                    )
                    if resp.headers.get("x-rate-limit-reset")
                    else None
                ),
            )
        except (ValueError, TypeError):
            pass


def _backoff(attempt: int) -> float:
    return min(30.0, (2 ** (attempt - 1)) * 0.5)


def _reset_seconds(resp: httpx.Response) -> int:
    reset = resp.headers.get("x-rate-limit-reset")
    if not reset:
        return 0
    try:
        delta = int(reset) - int(datetime.now(timezone.utc).timestamp())
        return max(0, delta)
    except ValueError:
        return 0


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _classify_type(raw: dict) -> PostType:
    refs = raw.get("referenced_tweets") or []
    kinds = {r.get("type") for r in refs}
    if "retweeted" in kinds:
        return "repost"
    if "quoted" in kinds:
        return "quote"
    if raw.get("in_reply_to_user_id") or "replied_to" in kinds:
        return "reply"
    return "original"


def _classify_media(raw: dict, urls: list[str]) -> MediaType:
    attachments = raw.get("attachments") or {}
    if attachments.get("poll_ids"):
        return "poll"
    if attachments.get("media_keys"):
        return "image"  # exact media type needs expansions; default to image
    if urls:
        return "link"
    return "none"


def _map_tweet(raw: dict) -> ProviderPost:
    pm = raw.get("public_metrics", {}) or {}
    entities = raw.get("entities", {}) or {}
    hashtags = [h.get("tag") for h in entities.get("hashtags", []) if h.get("tag")]
    mentions = [m.get("username") for m in entities.get("mentions", []) if m.get("username")]
    urls = [
        u.get("expanded_url") or u.get("url")
        for u in entities.get("urls", [])
        if (u.get("expanded_url") or u.get("url"))
    ]
    return ProviderPost(
        post_id=str(raw["id"]),
        text=raw.get("text", ""),
        created_at=_parse_dt(raw.get("created_at")) or datetime.now(timezone.utc),
        lang=raw.get("lang"),
        post_type=_classify_type(raw),
        media_type=_classify_media(raw, urls),
        like_count=pm.get("like_count", 0),
        reply_count=pm.get("reply_count", 0),
        repost_count=pm.get("retweet_count", 0),
        quote_count=pm.get("quote_count", 0),
        hashtags=hashtags,
        mentions=mentions,
        urls=urls,
        conversation_id=raw.get("conversation_id"),
        in_reply_to_user_id=raw.get("in_reply_to_user_id"),
    )
