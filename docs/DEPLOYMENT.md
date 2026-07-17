# Deployment guide

This guide covers deploying **X Behavior Analyzer** to a single Linux VPS with
Docker Compose, plus backup/restore and rollback procedures. The app is
structured so it can later move to AWS/Azure/GCP (managed Postgres + Redis,
containers on ECS/Cloud Run/AKS) without code changes.

## 1. Prerequisites

- A Linux VPS (2 vCPU / 4 GB RAM is comfortable) with a public IP.
- A domain name pointing an `A` record at the VPS.
- Docker Engine + Docker Compose plugin installed.
- Ports 80 and 443 open.

## 2. First deploy (demo mode, no X credentials)

```bash
git clone <your-repo-url> xba && cd xba
cp .env.example .env            # defaults to X_PROVIDER=mock
docker compose up -d --build
```

- App: http://SERVER_IP:8080
- The base compose file exposes only Nginx (port 8080). Backend, worker,
  Postgres, and Redis are on the internal network.

## 3. Production deploy (TLS + real data)

1. **Configure environment**

   ```bash
   cp .env.production.example .env
   # Generate secrets:
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   # Fill APP_SECRET_KEY, JWT_SECRET_KEY, POSTGRES_PASSWORD, DATABASE_URL,
   # and (for real data) X_PROVIDER=x_api + X_API_BEARER_TOKEN.
   ```

2. **Obtain TLS certificates** (Let's Encrypt example)

   ```bash
   sudo apt-get install -y certbot
   sudo certbot certonly --standalone -d your-domain.example
   mkdir -p certs
   sudo cp /etc/letsencrypt/live/your-domain.example/fullchain.pem certs/
   sudo cp /etc/letsencrypt/live/your-domain.example/privkey.pem  certs/
   sudo chown $USER certs/*.pem
   ```

3. **Launch with production overrides**

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

   - Nginx now serves 80 (→ redirect) and 443 (TLS).
   - Backend runs under Gunicorn + Uvicorn workers.
   - Migrations run automatically (`alembic upgrade head`) on backend start.

4. **(Optional) Seed demonstration data**

   ```bash
   docker compose exec backend python -m app.scripts.seed_demo
   ```

5. **Verify**

   ```bash
   curl -f https://your-domain.example/api/v1/health
   curl -f https://your-domain.example/api/v1/ready
   ```

## 4. Operations

### Logs & status
```bash
docker compose ps
docker compose logs -f backend worker
```

### Applying updates (with rollback safety)
```bash
git fetch && git checkout <new-tag>
# Back up first (see below), then:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec backend alembic upgrade head
```

### Database migrations
Migrations run on backend startup. To run manually:
```bash
docker compose exec backend alembic upgrade head       # apply
docker compose exec backend alembic downgrade -1       # revert last
docker compose exec backend alembic history            # list
```

## 5. Backup & restore

### Backup PostgreSQL
```bash
# Timestamped logical dump
docker compose exec -T postgres pg_dump -U xba xba \
  | gzip > backup-$(date +%F-%H%M).sql.gz
```

### Backup generated reports (PDF volume)
```bash
docker run --rm -v xba_reports:/data -v "$PWD":/backup alpine \
  tar czf /backup/reports-$(date +%F).tar.gz -C /data .
```

### Restore PostgreSQL
```bash
gunzip -c backup-YYYY-MM-DD-HHMM.sql.gz \
  | docker compose exec -T postgres psql -U xba -d xba
```

### Restore reports
```bash
docker run --rm -v xba_reports:/data -v "$PWD":/backup alpine \
  sh -c "cd /data && tar xzf /backup/reports-YYYY-MM-DD.tar.gz"
```

> Schedule backups with `cron` (e.g. nightly) and copy dumps off-box.

## 6. Rollback procedure

1. **Code rollback**
   ```bash
   git checkout <previous-good-tag>
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```
2. **Database rollback** — only if the new version applied a migration that must
   be reversed:
   ```bash
   docker compose exec backend alembic downgrade -1
   ```
   If a migration is not safely reversible, restore from the pre-deploy dump
   (section 5). **Always take a backup before deploying.**
3. **Verify** `GET /api/v1/ready` returns `200` and the dashboard loads.

## 7. Cloud portability notes

- **Database/Redis**: point `DATABASE_URL` / `REDIS_URL` at managed services
  (RDS/Cloud SQL, ElastiCache/Memorystore). No code change needed.
- **Containers**: the backend, worker, and frontend images run unchanged on
  ECS/Fargate, Cloud Run, or AKS. Run `alembic upgrade head` as a one-off task.
- **Object storage**: for horizontally-scaled report storage, mount a shared
  volume or adapt `report_service` to write to S3/GCS (single integration point).
- **Secrets**: use the platform secret manager; never bake secrets into images.
