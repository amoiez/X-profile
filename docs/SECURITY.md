# Security & privacy

## Scope and ethical limitations

X Behavior Analyzer analyzes **only publicly available** profile and post data
retrieved through the official X API. It reports **observable posting patterns**
and deliberately does **not**:

- determine personality, mental health, beliefs, intent, or criminality;
- infer political identity or other sensitive characteristics;
- claim an account is definitively automated or operated by a bot;
- access DMs, protected/private accounts, or deleted posts;
- present estimates as confirmed facts.

The "Possible Automation Pattern Score" is a transparent, deterministic sum of
individually-explained signals. Every report states that the score reflects
observable patterns and is **not proof** of automation, and reports with fewer
than `LOW_CONFIDENCE_POST_THRESHOLD` posts are flagged **Low confidence**.

## Data access rules

- The official X API is the production data source. The app never bypasses
  authentication, rate limits, CAPTCHAs, or access controls, and never scrapes.
- Protected/suspended/non-existent profiles are handled as explicit error states.
- Rate limits and `429` reset headers are respected; requests use timeouts and
  bounded retries with exponential backoff.

## Application security controls

| Area | Control |
|------|---------|
| Input validation | Username normalized/validated (1–15 `[A-Za-z0-9_]`); Pydantic models; post-limit bounds |
| Injection | All DB access via SQLAlchemy ORM (parameterized); no string-built SQL |
| AuthN/AuthZ | Optional JWT (Argon2 hashing); user-scoped analyses; admin role for monitoring |
| Rate limiting | Per-IP limits via slowapi; per-analysis hourly cap |
| Request limits | Body-size limit (413) at app + `client_max_body_size` at Nginx |
| CORS | Restricted to `FRONTEND_URL` |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP, HSTS (prod) |
| SSRF | No arbitrary user-supplied URLs are fetched by the backend; PDF rendering loads **no** remote resources |
| Secrets | Environment-only; never committed; token-bearing log keys redacted |
| Error handling | Stable error codes; internal traces never exposed in production |
| Containers | Non-root users in backend and frontend images; pinned dependencies |
| PDF safety | ReportLab renders offline from computed data only |

## Secrets management

- Copy `.env.example` / `.env.production.example` to `.env`; fill strong, unique
  values. `.env` is git-ignored.
- Rotate `JWT_SECRET_KEY`, `APP_SECRET_KEY`, database password, and the X bearer
  token periodically and on any suspected exposure.
- Logs never contain raw credentials (a redaction processor scrubs known keys),
  and full post bodies are not logged.

## Reporting

For security concerns, contact the repository owner. Do not open public issues
containing sensitive details or tokens.

## Known limitations

- Sentiment uses the English VADER lexicon; sarcasm/irony are not reliably
  detected, and unsupported languages return "sentiment unavailable".
- Engagement accumulates over time; recent posts may appear to underperform.
- Analyses reflect only the retrieved sample of recent public posts.
