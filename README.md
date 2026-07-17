# X Behavior Analyzer

A production-ready **behavior analysis system** for public X (formerly Twitter)
profiles. Enter a public username and the app retrieves permitted public profile
and post data through the official X API, analyzes **observable posting
behavior**, and produces a professional dashboard plus a downloadable PDF report.

> **Scope & ethics.** This system analyzes public activity only. It reports
> **observable posting patterns** and does **not** determine private intentions,
> mental health, criminality, political identity, personality, or whether an
> account is definitively automated. Pattern scores describe observable signals,
> not confirmed facts. Reports with fewer than 10 posts are flagged **low
> confidence**, and mock results are always labeled as demonstration data.

---

## Features

- 🔎 **Analyze any public X profile** by username (with or without `@`).
- ⚙️ **Asynchronous jobs** — submit and get a job id instantly; watch staged
  progress via polling.
- 📊 **Professional dashboard** — profile header, executive summary, metric
  cards, and charts (weekly activity, hourly heatmap, sentiment doughnut +
  trend, topics, engagement, automation-score gauge, top-posts table).
- 🧾 **Downloadable 15-section PDF report** with methodology, data limitations,
  and an ethical-use disclaimer.
- 🕓 **History** — list, view, refresh, and delete previous analyses.
- 🤖 **Transparent automation-pattern score (0–100)** — a deterministic sum of
  six explained components; never a black box, always with a "not proof of a
  bot" disclaimer.
- 🧪 **Demo mode with zero credentials** — a deterministic mock provider powers
  local dev, tests, and demos; swap to the real X API with one env var.
- 🔐 **Optional auth**, per-IP rate limiting, security headers, SSRF-safe PDF
  rendering, and structured JSON logging.

## What it analyzes

| Group | Examples |
|-------|----------|
| **Activity** | posts/day & /week, median interval, most active hour/weekday, hourly & weekly distributions, original/reply/repost composition, consistency, longest gap, bursts |
| **Content** | top keywords/hashtags/mentions/domains, dominant topics, media usage, average length, repeated phrases, duplicate/near-duplicate ratio |
| **Sentiment** | positive/neutral/negative distribution, average score, daily trend, by-hashtag (English VADER; unsupported languages → "unavailable") |
| **Engagement** | avg/median/total likes, replies, reposts, quotes; approximate rate; top posts; by content-type/weekday/hour |
| **Patterns** | 10 observable indicators + the automation-pattern score with per-signal explanations |

All timezone-sensitive metrics honor the report timezone (default UTC).

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 · TypeScript · Tailwind CSS · Recharts · TanStack Query · React Hook Form · Zod |
| Backend | Python 3.11 · FastAPI · SQLAlchemy 2 (async) · Alembic · Pydantic · HTTPX |
| Analysis / NLP | pandas · VADER (sentiment) · langdetect · standard-library metric engines |
| Reports | ReportLab (PDF) |
| Data / infra | PostgreSQL (JSONB) · Redis (queue/cache) · async worker · Nginx · Docker Compose |
| Security | Argon2 · JWT · slowapi rate limiting · CORS · security headers |
| CI | GitHub Actions (lint, tests, coverage gate, Docker build, dependency scan) |

## Architecture

```
Nginx (reverse proxy, security headers, TLS)
  ├── frontend  — Next.js + TypeScript + Tailwind + Recharts + TanStack Query
  └── backend   — FastAPI + SQLAlchemy + Pydantic + HTTPX
        ├── worker — async analysis job processing (Redis queue)
        ├── PostgreSQL — users, profiles, jobs, results, reports (JSONB metrics)
        └── Redis — queue, caching, job progress, rate limiting
```

**Provider abstraction** (`backend/app/providers/`) lets the app run against:

- `MockXProvider` — deterministic demo/test data, **no credentials required**.
- `XApiProvider` — real production data via the official X API v2 (timeouts,
  backoff, 429 handling, pagination, error mapping, no token logging).

If `X_PROVIDER=x_api` but no bearer token is set, the app **automatically falls
back to mock mode** so it always runs.

## Quick start (Docker, demo mode)

```bash
cp .env.example .env          # defaults to X_PROVIDER=mock (no credentials)
docker compose up --build
```

- App (via Nginx): http://localhost:8080
- Health check: http://localhost:8080/api/v1/health
- Interactive API docs: `/docs` on the backend service

Docker Compose starts all six services: **frontend, backend, worker,
PostgreSQL, Redis, Nginx**.

## Local development (without Docker)

**Backend**
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="sqlite+aiosqlite:///./dev.db"   # PowerShell: $env:DATABASE_URL=...
alembic upgrade head
uvicorn app.main:app --reload                        # http://localhost:8000

# In a second shell, start the worker (optional — inline fallback works without it):
python -m app.workers.run_worker

# Seed demonstration analyses:
python -m app.scripts.seed_demo
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                                          # http://localhost:3000
```

## Reserved demo usernames (mock provider)

| Username | Behavior |
|----------|----------|
| `notfound_demo` | `PROFILE_NOT_FOUND` |
| `protected_demo` | `PROFILE_PROTECTED` |
| `suspended_demo` | `PROFILE_SUSPENDED` |
| `empty_demo` | Valid profile with **no posts** |
| `*bot*` (e.g. `news_bot`) | High-regularity, duplicate-heavy "automation-like" pattern |
| anything else | A stable, realistic synthetic profile |

## API (v1)

Base path `/api/v1`. All errors use a consistent envelope
(`{ "error": { "code", "message", "request_id" } }`).

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health`, `/ready` | Liveness / readiness (DB + Redis checks) |
| `POST` | `/analyses` | Create an analysis job (returns job id) |
| `GET` | `/analyses/{id}` | Job summary |
| `GET` | `/analyses/{id}/progress` | Progress for polling/SSE |
| `GET` | `/analyses/{id}/results` | Full computed metrics + summary |
| `GET` | `/analyses` | Paginated history |
| `POST` | `/analyses/{id}/refresh` | Re-run the analysis |
| `DELETE` | `/analyses/{id}` | Delete a job and its data |
| `GET` | `/analyses/{id}/report.pdf` | Download the PDF report |
| `POST` | `/auth/register`, `/auth/login`, `/auth/refresh` | Optional local auth |
| `GET` | `/auth/me` | Current user |
| `GET` | `/admin/stats` | Monitoring (admin only) |

Full reference: [docs/API.md](docs/API.md).

## Project structure

```
.
├── backend/            FastAPI app, analytics engines, providers, reports, tests
│   ├── app/
│   │   ├── analytics/  activity, content, sentiment, engagement, scoring, patterns
│   │   ├── api/         health, analyses, auth, admin routers
│   │   ├── providers/  base, mock_x, x_api, factory
│   │   ├── reports/    ReportLab PDF generator
│   │   ├── services/   job pipeline, queue, report + auth services
│   │   └── tests/      104 tests (pytest)
│   └── alembic/        migrations
├── frontend/           Next.js dashboard, charts, pages, vitest tests
├── nginx/              dev + prod (TLS) reverse-proxy configs
├── docs/               ARCHITECTURE, API, DEPLOYMENT, SECURITY
├── docker-compose.yml  full stack
├── docker-compose.prod.yml
└── .github/workflows/  CI pipeline
```

## Configuration

All configuration is via environment variables — see
[.env.example](.env.example) (dev) and
[.env.production.example](.env.production.example) (prod). Secrets are never
committed or logged. The default local configuration uses the mock provider.

## Production deployment

```bash
cp .env.production.example .env      # fill strong secrets; set X_PROVIDER=x_api for real data
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec backend python -m app.scripts.seed_demo   # optional demo data
```

Nginx terminates TLS on 80/443. Full instructions — Let's Encrypt, backups,
restore, and rollback — are in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Testing

```bash
# Backend — 104 tests
cd backend && pytest
pytest --cov=app/analytics --cov=app/services --cov-report=term-missing

# Frontend — component + validation tests, typecheck, build
cd frontend && npm run test && npm run typecheck && npm run build
```

CI runs lint (ruff / ESLint), the full test suites with an 80% coverage gate on
analytics + scoring, Docker image builds, and a dependency scan on every push
and pull request.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design & request lifecycle
- [docs/API.md](docs/API.md) — API reference
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — VPS deploy, backup/restore, rollback
- [docs/SECURITY.md](docs/SECURITY.md) — security controls, privacy & ethical limitations

## License / use

For authorized analysis of **public** data only. Do not use to harass, profile,
or make consequential decisions about individuals.
