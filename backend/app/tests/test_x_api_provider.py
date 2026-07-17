"""XApiProvider error-mapping and parsing tests using a mocked HTTP transport."""

from __future__ import annotations

import httpx
import pytest

from app.core.config import settings
from app.core.errors import (
    CredentialsMissingError,
    ProfileNotFoundError,
    ProfileProtectedError,
    ProfileSuspendedError,
    ProviderError,
    RateLimitedError,
)
from app.providers.base import ProviderProfile
from app.providers.x_api import XApiProvider


@pytest.fixture(autouse=True)
def _creds(monkeypatch):
    # Provide a token and disable retry backoff for fast, deterministic tests.
    monkeypatch.setattr(settings, "x_api_bearer_token", "test-token")
    monkeypatch.setattr(settings, "x_max_retries", 0)


def _provider(handler) -> XApiProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url=settings.x_api_base_url)
    return XApiProvider(client=client)


def test_missing_credentials_raises(monkeypatch):
    monkeypatch.setattr(settings, "x_api_bearer_token", "")
    with pytest.raises(CredentialsMissingError):
        XApiProvider()


async def test_get_user_success():
    def handler(request):
        return httpx.Response(200, json={
            "data": {
                "id": "42", "username": "openai", "name": "OpenAI",
                "description": "AI", "protected": False, "verified": True,
                "created_at": "2011-01-01T00:00:00.000Z",
                "public_metrics": {"followers_count": 100, "following_count": 5,
                                   "tweet_count": 500, "listed_count": 10},
                "profile_image_url": "https://x/img.png",
            }
        })
    prof = await _provider(handler).get_user_by_username("@openai")
    assert isinstance(prof, ProviderProfile)
    assert prof.platform_user_id == "42"
    assert prof.followers_count == 100
    assert prof.verified is True


async def test_protected_profile():
    def handler(request):
        return httpx.Response(200, json={"data": {"id": "1", "username": "x", "protected": True}})
    with pytest.raises(ProfileProtectedError):
        await _provider(handler).get_user_by_username("x")


async def test_not_found():
    def handler(request):
        return httpx.Response(200, json={"errors": [{"title": "Not Found Error"}]})
    with pytest.raises(ProfileNotFoundError):
        await _provider(handler).get_user_by_username("ghost")


async def test_suspended():
    def handler(request):
        return httpx.Response(200, json={"errors": [{"title": "Forbidden: suspended"}]})
    with pytest.raises(ProfileSuspendedError):
        await _provider(handler).get_user_by_username("banned")


async def test_http_404_maps_not_found():
    def handler(request):
        return httpx.Response(404, json={})
    with pytest.raises(ProfileNotFoundError):
        await _provider(handler).get_user_by_username("ghost")


async def test_http_401_maps_credentials():
    def handler(request):
        return httpx.Response(401, json={})
    with pytest.raises(CredentialsMissingError):
        await _provider(handler).get_user_by_username("x")


async def test_http_403_maps_protected():
    def handler(request):
        return httpx.Response(403, json={})
    with pytest.raises(ProfileProtectedError):
        await _provider(handler).get_user_by_username("x")


async def test_rate_limited():
    def handler(request):
        return httpx.Response(429, headers={"x-rate-limit-reset": "9999999999"}, json={})
    with pytest.raises(RateLimitedError):
        await _provider(handler).get_user_by_username("x")


async def test_server_error_maps_provider_error():
    def handler(request):
        return httpx.Response(503, json={})
    with pytest.raises(ProviderError):
        await _provider(handler).get_user_by_username("x")


async def test_timeout_maps_network_error():
    def handler(request):
        raise httpx.TimeoutException("timed out")
    with pytest.raises(ProviderError):  # ErrorCode.NETWORK_ERROR
        await _provider(handler).get_user_by_username("x")


async def test_get_user_posts_paginates_and_maps():
    calls = {"n": 0}

    def handler(request):
        if "/tweets" in request.url.path:
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(200, json={
                    "data": [
                        {"id": "1", "text": "hello #ai @bob http://example.com",
                         "created_at": "2026-01-01T00:00:00.000Z", "lang": "en",
                         "public_metrics": {"like_count": 5, "reply_count": 1,
                                            "retweet_count": 2, "quote_count": 0},
                         "entities": {"hashtags": [{"tag": "ai"}],
                                      "mentions": [{"username": "bob"}],
                                      "urls": [{"expanded_url": "http://example.com"}]}},
                    ],
                    "meta": {"next_token": "TOKEN2"},
                })
            return httpx.Response(200, json={
                "data": [{"id": "2", "text": "second",
                          "created_at": "2026-01-02T00:00:00.000Z", "lang": "en",
                          "referenced_tweets": [{"type": "retweeted", "id": "9"}],
                          "public_metrics": {"like_count": 0}}],
                "meta": {},
            })
        return httpx.Response(200, json={"data": {"id": "42", "username": "u"}})

    provider = _provider(handler)
    prof = ProviderProfile(platform_user_id="42", username="u")
    posts = await provider.get_user_posts(prof, limit=200)
    assert len(posts) == 2
    assert posts[0].hashtags == ["ai"]
    assert posts[0].mentions == ["bob"]
    assert posts[0].like_count == 5
    assert posts[1].post_type == "repost"
