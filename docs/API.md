# API Reference (v1)

Base path: `/api/v1`. All responses are JSON. Errors use a consistent envelope.

## Error format

```json
{
  "error": {
    "code": "PROFILE_PROTECTED",
    "message": "This profile is protected and cannot be analyzed.",
    "request_id": "3f1c…"
  }
}
```

### Error codes

`INVALID_USERNAME`, `PROFILE_NOT_FOUND`, `PROFILE_PROTECTED`,
`PROFILE_SUSPENDED`, `NO_POSTS_AVAILABLE`, `CREDENTIALS_MISSING`,
`RATE_LIMITED`, `UNSUPPORTED_LANGUAGE`, `ANALYSIS_FAILED`, `NETWORK_ERROR`,
`PROVIDER_ERROR`, `NOT_FOUND`, `VALIDATION_ERROR`, `INTERNAL_ERROR`.

## Health

### `GET /api/v1/health`
Liveness. `200 { "status": "ok", "service": "xba-backend" }`.

### `GET /api/v1/ready`
Readiness. Checks DB and Redis. `503` if not ready.

```json
{ "status": "ready", "checks": { "database": "ok", "redis": "ok", "provider": "mock" } }
```

## Analyses  *(implemented in Milestone 2)*

### `POST /api/v1/analyses`
Create an analysis job. Returns a job id immediately.

```json
// request
{ "username": "@example", "post_limit": 200, "timezone": "Asia/Karachi", "force_refresh": false }
```

### `GET /api/v1/analyses/{job_id}`
Job summary (status, progress, counts, data source).

### `GET /api/v1/analyses/{job_id}/progress`
Lightweight progress payload for polling/SSE.

### `GET /api/v1/analyses/{job_id}/results`
Full computed metrics + summary + data-quality block.

### `GET /api/v1/analyses`
Paginated history (`?page=&page_size=`).

### `DELETE /api/v1/analyses/{job_id}`
Delete a job and its results/reports (cascade).

### `POST /api/v1/analyses/{job_id}/refresh`
Re-run analysis for the same username.

### `GET /api/v1/analyses/{job_id}/report.pdf`
Generate (if needed) and download the PDF report for a completed job. Pass
`?force=true` to regenerate. Returns `409` if the job is not completed. The
15-section report includes profile overview, executive summary, activity,
content, sentiment, engagement, pattern indicators, the automation-pattern
score, methodology, data limitations, and the ethical-use disclaimer.
