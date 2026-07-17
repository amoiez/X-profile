# Architecture

## Overview

X Behavior Analyzer is a containerized full-stack application that analyzes
**observable public posting behavior** of X profiles. It is deliberately
constrained to public data and observable signals; it never infers private
traits.

## Services

| Service | Tech | Responsibility |
|---------|------|----------------|
| `frontend` | Next.js/TS, Tailwind, Recharts, TanStack Query | Input, progress, dashboard, history, PDF download |
| `backend` | FastAPI, SQLAlchemy, Pydantic, HTTPX, Pandas | Validation, provider integration, DB, analytics, reports |
| `worker` | Python asyncio (Redis-backed queue) | Async analysis job processing |
| `postgres` | PostgreSQL 16 | Persistent storage (JSONB metrics) |
| `redis` | Redis 7 | Queue, cache, job progress, rate limiting |
| `nginx` | Nginx | Reverse proxy, security headers, TLS termination |

## Request lifecycle

1. `POST /api/v1/analyses` with a username → validate & normalize.
2. Provider resolves the profile (mock or real). Errors map to stable codes.
3. A job row is created (`pending`); the job id is returned immediately.
4. The worker retrieves posts, then runs five analytics engines:
   `activity → content → sentiment → engagement → patterns`.
5. Deterministic scoring produces the automation-pattern score with per-signal
   explanations.
6. A template summary is generated using careful, non-diagnostic language.
7. Results persist as JSONB; progress is streamed via polling/SSE.
8. A PDF report can be generated on demand.

## Provider abstraction

`providers/base.py` defines `BaseXProvider` returning normalized
`ProviderProfile` / `ProviderPost` objects. `factory.get_provider()` selects
`MockXProvider` or `XApiProvider` from config, falling back to mock when real
credentials are absent. This keeps the analytics engine provider-agnostic and
guarantees the app always runs.

## Data model

- `users` — optional local auth (role-based).
- `x_profiles` — cached public profile blobs (`public_profile_data` JSONB).
- `analysis_jobs` — one per request; status, progress, stage, period, source.
- `analysis_results` — JSONB metric groups + summary + data-quality + version.
- `reports` — generated PDF metadata (path, format, timestamp).

Portable column types (`GUID`, `PortableJSON`) let the same models run on
PostgreSQL (JSONB) and SQLite (JSON) for local dev and tests.

## Ethical & safety design

- Automation-pattern score is **transparent and deterministic** — every
  contributing signal is stored and shown, with the disclaimer that the score
  is not proof of automation.
- Reports with `< LOW_CONFIDENCE_POST_THRESHOLD` posts are flagged
  **Low confidence**.
- Summaries use hedged templates ("The collected posts indicate…"); no
  personality/psychology/identity claims.
- No arbitrary user-supplied URLs are fetched by the backend (SSRF guard).
- Secrets only via environment; tokens never logged.
