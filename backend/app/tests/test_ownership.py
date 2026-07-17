"""Analyses are scoped to their owner; anonymous jobs stay anonymous."""

from __future__ import annotations


async def _auth_headers(client, email):
    reg = await client.post("/api/v1/auth/register",
                           json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


async def test_owned_job_hidden_from_other_user(client):
    a = await _auth_headers(client, "a@example.com")
    b = await _auth_headers(client, "b@example.com")

    created = await client.post("/api/v1/analyses", json={"username": "owned_user"}, headers=a)
    job_id = created.json()["id"]

    # owner can read
    assert (await client.get(f"/api/v1/analyses/{job_id}", headers=a)).status_code == 200
    # other user gets 404 (ownership not leaked)
    assert (await client.get(f"/api/v1/analyses/{job_id}", headers=b)).status_code == 404
    # anonymous gets 404 too
    assert (await client.get(f"/api/v1/analyses/{job_id}")).status_code == 404


async def test_history_is_scoped(client):
    a = await _auth_headers(client, "hist_a@example.com")
    b = await _auth_headers(client, "hist_b@example.com")
    await client.post("/api/v1/analyses", json={"username": "a_one"}, headers=a)
    await client.post("/api/v1/analyses", json={"username": "a_two"}, headers=a)
    await client.post("/api/v1/analyses", json={"username": "b_one"}, headers=b)

    list_a = await client.get("/api/v1/analyses", headers=a)
    assert list_a.json()["total"] == 2
    list_b = await client.get("/api/v1/analyses", headers=b)
    assert list_b.json()["total"] == 1


async def test_anonymous_history_excludes_owned(client):
    a = await _auth_headers(client, "anon_owner@example.com")
    await client.post("/api/v1/analyses", json={"username": "owned_only"}, headers=a)
    await client.post("/api/v1/analyses", json={"username": "anon_only"})

    anon_list = await client.get("/api/v1/analyses")
    usernames = {item["username"] for item in anon_list.json()["items"]}
    assert "anon_only" in usernames
    assert "owned_only" not in usernames


async def test_other_user_cannot_delete(client):
    a = await _auth_headers(client, "del_a@example.com")
    b = await _auth_headers(client, "del_b@example.com")
    created = await client.post("/api/v1/analyses", json={"username": "to_delete"}, headers=a)
    job_id = created.json()["id"]
    assert (await client.delete(f"/api/v1/analyses/{job_id}", headers=b)).status_code == 404
    assert (await client.delete(f"/api/v1/analyses/{job_id}", headers=a)).status_code == 204
