import pytest

from app.core.errors import (
    ProfileNotFoundError,
    ProfileProtectedError,
    ProfileSuspendedError,
)
from app.providers.mock_x import MockXProvider


@pytest.fixture
def provider():
    return MockXProvider()


async def test_profile_is_deterministic(provider):
    a = await provider.get_user_by_username("openai")
    b = await provider.get_user_by_username("@openai")
    assert a.platform_user_id == b.platform_user_id
    assert a.followers_count == b.followers_count
    assert a.username == "openai"


async def test_posts_are_deterministic_and_bounded(provider):
    prof = await provider.get_user_by_username("some_user")
    p1 = await provider.get_user_posts(prof, limit=50)
    p2 = await provider.get_user_posts(prof, limit=50)
    assert [p.post_id for p in p1] == [p.post_id for p in p2]
    assert len(p1) <= 50
    # newest first (descending created_at)
    times = [p.created_at for p in p1]
    assert times == sorted(times, reverse=True)


async def test_reserved_not_found(provider):
    with pytest.raises(ProfileNotFoundError):
        await provider.get_user_by_username("notfound_demo")


async def test_reserved_protected(provider):
    with pytest.raises(ProfileProtectedError):
        await provider.get_user_by_username("protected_demo")


async def test_reserved_suspended(provider):
    with pytest.raises(ProfileSuspendedError):
        await provider.get_user_by_username("suspended_demo")


async def test_reserved_empty_has_no_posts(provider):
    prof = await provider.get_user_by_username("empty_demo")
    posts = await provider.get_user_posts(prof, limit=100)
    assert posts == []


async def test_botlike_username_is_regular(provider):
    prof = await provider.get_user_by_username("news_bot")
    posts = await provider.get_user_posts(prof, limit=100)
    assert len(posts) > 0
    assert all(p.lang == "en" for p in posts)
