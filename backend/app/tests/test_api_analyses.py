"""API tests for the analysis endpoints (mock provider, inline execution)."""

from __future__ import annotations


async def test_health(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_create_and_get_results(client):
    r = await client.post("/api/v1/analyses", json={"username": "@sample_user", "post_limit": 60})
    assert r.status_code == 202, r.text
    job = r.json()
    assert job["username"] == "sample_user"
    job_id = job["id"]

    # Completed via inline sync execution.
    r2 = await client.get(f"/api/v1/analyses/{job_id}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"

    r3 = await client.get(f"/api/v1/analyses/{job_id}/results")
    assert r3.status_code == 200
    body = r3.json()
    assert body["activity_metrics"]["post_count"] > 0
    assert body["data_quality"]["data_source"] == "mock"
    assert body["data_quality"]["is_mock"] is True
    assert "headline" in body["summary"]


async def test_import_csv_analysis(client):
    csv_text = (
        "created_at,text,like_count,reply_count,repost_count,quote_count\n"
        "2026-07-18T10:00:00Z,\"Building in public #ai\",10,2,3,1\n"
        "2026-07-17T09:30:00Z,\"Another update @team\",8,1,2,0\n"
    )
    r = await client.post(
        "/api/v1/analyses/import",
        json={"username": "imported_user", "csv_text": csv_text},
    )

    assert r.status_code == 202, r.text
    job_id = r.json()["id"]
    assert r.json()["status"] == "completed"

    results = await client.get(f"/api/v1/analyses/{job_id}/results")
    body = results.json()
    assert body["data_quality"]["data_source"] == "import"
    assert body["data_quality"]["is_imported"] is True
    assert body["activity_metrics"]["post_count"] == 2


async def test_import_csv_requires_dates(client):
    csv_text = "text,like_count\n\"No timestamp\",10\n"
    r = await client.post(
        "/api/v1/analyses/import",
        json={"username": "imported_user", "csv_text": csv_text},
    )

    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_invalid_username_rejected(client):
    r = await client.post("/api/v1/analyses", json={"username": "bad handle!"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_USERNAME"


async def test_arbitrary_username_rejected_in_restricted_mock_mode(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "allow_arbitrary_mock_profiles", False)

    r = await client.post("/api/v1/analyses", json={"username": "real_handle"})

    assert r.status_code == 503
    assert r.json()["error"]["code"] == "CREDENTIALS_MISSING"


async def test_post_limit_bounds(client):
    r = await client.post("/api/v1/analyses", json={"username": "user", "post_limit": 999999})
    assert r.status_code == 422  # exceeds configured max


async def test_protected_profile_fails_job(client):
    r = await client.post("/api/v1/analyses", json={"username": "protected_demo"})
    assert r.status_code == 202
    job_id = r.json()["id"]
    r2 = await client.get(f"/api/v1/analyses/{job_id}")
    assert r2.json()["status"] == "failed"
    assert r2.json()["error_code"] == "PROFILE_PROTECTED"


async def test_empty_profile_no_posts(client):
    r = await client.post("/api/v1/analyses", json={"username": "empty_demo"})
    job_id = r.json()["id"]
    r2 = await client.get(f"/api/v1/analyses/{job_id}")
    assert r2.json()["status"] == "failed"
    assert r2.json()["error_code"] == "NO_POSTS_AVAILABLE"


async def test_not_found_profile(client):
    r = await client.post("/api/v1/analyses", json={"username": "notfound_demo"})
    job_id = r.json()["id"]
    r2 = await client.get(f"/api/v1/analyses/{job_id}")
    assert r2.json()["status"] == "failed"
    assert r2.json()["error_code"] == "PROFILE_NOT_FOUND"


async def test_list_and_delete(client):
    await client.post("/api/v1/analyses", json={"username": "user_one"})
    await client.post("/api/v1/analyses", json={"username": "user_two"})
    lst = await client.get("/api/v1/analyses?page=1&page_size=10")
    assert lst.status_code == 200
    assert lst.json()["total"] >= 2

    first_id = lst.json()["items"][0]["id"]
    d = await client.delete(f"/api/v1/analyses/{first_id}")
    assert d.status_code == 204
    g = await client.get(f"/api/v1/analyses/{first_id}")
    assert g.status_code == 404


async def test_refresh_creates_new_job(client):
    r = await client.post("/api/v1/analyses", json={"username": "refresh_me"})
    old_id = r.json()["id"]
    rf = await client.post(f"/api/v1/analyses/{old_id}/refresh")
    assert rf.status_code == 202
    assert rf.json()["id"] != old_id
    assert rf.json()["username"] == "refresh_me"


async def test_download_report_pdf(client):
    r = await client.post("/api/v1/analyses", json={"username": "report_user", "post_limit": 60})
    job_id = r.json()["id"]
    pdf = await client.get(f"/api/v1/analyses/{job_id}/report.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:5] == b"%PDF-"


async def test_report_rejected_for_failed_job(client):
    r = await client.post("/api/v1/analyses", json={"username": "protected_demo"})
    job_id = r.json()["id"]
    pdf = await client.get(f"/api/v1/analyses/{job_id}/report.pdf")
    assert pdf.status_code == 409


async def test_progress_endpoint(client):
    r = await client.post("/api/v1/analyses", json={"username": "progress_user"})
    job_id = r.json()["id"]
    p = await client.get(f"/api/v1/analyses/{job_id}/progress")
    assert p.status_code == 200
    assert p.json()["progress"] == 100
    assert p.json()["status"] == "completed"
