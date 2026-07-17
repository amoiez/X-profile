"""Authentication and authorization tests."""

from __future__ import annotations

from app.database.session import AsyncSessionLocal
from app.models.user import UserRole
from app.services import auth_service


async def test_register_and_login(client):
    r = await client.post("/api/v1/auth/register",
                          json={"email": "user@example.com", "password": "supersecret1"})
    assert r.status_code == 201, r.text
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    # duplicate registration rejected
    dup = await client.post("/api/v1/auth/register",
                           json={"email": "user@example.com", "password": "supersecret1"})
    assert dup.status_code == 409

    login = await client.post("/api/v1/auth/login",
                             json={"email": "user@example.com", "password": "supersecret1"})
    assert login.status_code == 200

    bad = await client.post("/api/v1/auth/login",
                           json={"email": "user@example.com", "password": "wrongpass1"})
    assert bad.status_code == 401


async def test_me_requires_auth(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401

    reg = await client.post("/api/v1/auth/register",
                           json={"email": "me@example.com", "password": "supersecret1"})
    token = reg.json()["access_token"]
    r2 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["email"] == "me@example.com"


async def test_refresh_token(client):
    reg = await client.post("/api/v1/auth/register",
                           json={"email": "r@example.com", "password": "supersecret1"})
    refresh = reg.json()["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert r.json()["access_token"]

    # access token cannot be used as a refresh token
    access = reg.json()["access_token"]
    bad = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert bad.status_code == 401


async def test_admin_stats_requires_admin(client):
    # normal user forbidden
    reg = await client.post("/api/v1/auth/register",
                           json={"email": "plain@example.com", "password": "supersecret1"})
    token = reg.json()["access_token"]
    forbidden = await client.get("/api/v1/admin/stats",
                                headers={"Authorization": f"Bearer {token}"})
    assert forbidden.status_code == 403

    # unauthenticated => 401
    anon = await client.get("/api/v1/admin/stats")
    assert anon.status_code == 401

    # promote to admin and retry
    async with AsyncSessionLocal() as s:
        admin = await auth_service.register_user(
            s, email="admin@example.com", password="supersecret1", role=UserRole.ADMIN
        )
    from app.core.security import create_access_token

    admin_token = create_access_token(admin.id, "admin")
    ok = await client.get("/api/v1/admin/stats",
                         headers={"Authorization": f"Bearer {admin_token}"})
    assert ok.status_code == 200
    assert "jobs_by_status" in ok.json()
