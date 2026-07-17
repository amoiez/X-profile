# X Behavior Analyzer

A **behavior analysis system** for public X (formerly Twitter) profiles. Enter a
public username and the app retrieves permitted public profile and post data
through the official X API, analyzes **observable posting behavior**, and
produces a professional dashboard plus a downloadable PDF report.

> **Scope & ethics.** This system analyzes public activity only. It reports
> **observable posting patterns** and does **not** determine private
> intentions, mental health, criminality, political identity, personality, or
> whether an account is definitively automated. Pattern scores describe
> observable signals, not confirmed facts.

---

## Status

Built milestone by milestone. Current progress:

| Milestone | Scope | Status |
|-----------|-------|--------|
| 1 | Architecture, env, Docker, DB models, mock provider | ✅ Done |
| 2 | Analysis job API, worker, activity analytics, tests | ⏳ Next |
| 3 | Content, sentiment, engagement, pattern analysis | ⏳ |
| 4 | Dashboard, charts, progress, history, error states | ⏳ |
| 5 | PDF reports + real X API provider | ⏳ |
| 6 | Auth, security hardening, rate limiting, CI/CD | ⏳ |
| 7 | Production deployment docs + final QA | ⏳ |

## Architecture

```
Nginx (reverse proxy, security headers, TLS)
  ├── frontend  — Next.js + TypeScript + Tailwind + Recharts + TanStack Query
  └── backend   — FastAPI + SQLAlchemy + Pydantic + HTTPX + Pandas
        ├── worker — async analysis job processing
        ├── PostgreSQL — users, profiles, jobs, results, reports (JSONB metrics)
        └── Redis — queues, caching, job progress, rate limiting
```

**Provider abstraction** (`backend/app/providers/`) lets the app run against:

- `MockXProvider` — deterministic demo/test data, **no credentials required**.
- `XApiProvider` — real production data via the official X API v2.

If `X_PROVIDER=x_api` but no bearer token is set, the app **automatically falls
back to mock mode** so it always runs. Mock results are clearly labeled
(`data_source: "mock"`).

## Quick start (Docker, demo mode)

```bash
cp .env.example .env          # defaults to X_PROVIDER=mock (no credentials)
docker compose up --build
```

- App (via Nginx):  http://localhost:8080
- Backend API docs: http://localhost:8080/api/v1/health  (and `/docs` on the backend)

## Local backend development (without Docker)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Use SQLite locally (no Postgres needed):
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"   # PowerShell: $env:DATABASE_URL=...
alembic upgrade head
uvicorn app.main:app --reload
```

### Run tests

```bash
cd backend
pytest                     # all tests
pytest --cov=app           # with coverage
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

## Configuration

All configuration is via environment variables — see [.env.example](.env.example).
Secrets are never committed or logged.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design
- [docs/API.md](docs/API.md) — API reference
- `docs/DEPLOYMENT.md`, `docs/SECURITY.md` — added in later milestones

## License / use

For authorized analysis of **public** data only. Do not use to harass,
profile, or make consequential decisions about individuals.
