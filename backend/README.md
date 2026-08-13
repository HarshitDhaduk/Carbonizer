# Carbonizer — Backend (FastAPI)

Async Python API for Carbonizer. FastAPI + Pydantic v2 + SQLAlchemy 2.0 (async) +
Alembic + PostgreSQL. Implements [docs/API-DESIGN.md](../docs/API-DESIGN.md) over the
schema in [docs/DB-SCHEMA.md](../docs/DB-SCHEMA.md).

## Quick start (no database needed)

`USE_DB=false` (the default) serves seed data that matches the frontend fixtures, so
the API runs with zero infrastructure:

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux:  source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime deps + pytest/httpx
cp .env.example .env

uvicorn app.main:app --reload          # http://localhost:8000
```

- Swagger UI → http://localhost:8000/docs
- ReDoc → http://localhost:8000/redoc
- OpenAPI → http://localhost:8000/api/v1/openapi.json

### Demo auth

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=demo@carbonizer.app&password=demo12345"
```

Returns `{ "accessToken": "…" }` — send it as `Authorization: Bearer <token>` for
protected routes (`/auth/me`, `/connections/*/link`, `/privacy/*`). The dashboard
read endpoints are public in seed mode so the frontend works immediately.

## Wire up the frontend

Point the Next.js client at this API (responses are camelCase to match the TS types):

```bash
# frontend/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## Endpoints (`/api/v1`)

| Group | Routes |
|---|---|
| health | `GET /healthz` · `GET /readyz` |
| auth | `POST /auth/register` · `POST /auth/login` · `GET /auth/me` |
| connections | `GET /connections` · `POST /connections/{provider}/link` · `POST /connections/{provider}/sync` |
| ingest | `POST /ingest/transactions` · `/trips` · `/energy` |
| footprint | `GET /footprint/summary?range=12w\|6m\|1y` |
| recommendations | `GET /recommendations` · `POST /{id}/act` · `POST /{id}/dismiss` |
| community | `GET /community/benchmark` |
| privacy | `GET /privacy/consents` · `GET\|PATCH /privacy/settings` · `POST /privacy/export` · `POST /privacy/erase` |

## With PostgreSQL (real data)

**1. Provision the role + database** (once, as the postgres superuser):

```bash
# from backend/ — psql prompts for the postgres password
psql -h 127.0.0.1 -U postgres -d postgres -f scripts/provision_db.sql
```

Creates role `carbonizer` (password `carbonizer`) and a database it owns. Idempotent.

**2. Configure `.env`:**

```bash
USE_DB=true
DATABASE_URL=postgresql+asyncpg://carbonizer:carbonizer@127.0.0.1:5432/carbonizer
```

> Use `127.0.0.1`, not `localhost` — asyncpg may otherwise resolve to IPv6 `::1`
> while Postgres answers on IPv4.

**3. Create the schema (Alembic) + seed the demo user's data:**

```bash
alembic upgrade head         # applies alembic/versions/*_init_schema.py
python -m app.db.seed_db     # demo user, footprint, nudges, cohort, connections
```

That's it — the dashboard endpoints now read from Postgres. The read queries live in
[app/services/dashboard.py](app/services/dashboard.py) (snapshot → summary, ranked
recommendations, cohort join with k-anonymity, connections with relative timestamps).
`GET /footprint/summary` is served from the `footprint_snapshots.payload` cache.

**Auth (DB mode):** real accounts with Argon2-hashed passwords.

```bash
# register → 201 { accessToken } (409 if the email is taken)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"s3cretpw123","region":"GB"}'

# login verifies the hash from Postgres; the JWT subject is the user's UUID
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=you@example.com&password=s3cretpw123"
```

(`auth/register` returns `503` in seed mode — it requires `USE_DB=true`.)

### Migrations (Alembic)

The initial migration (`init schema`) is committed under `alembic/versions/`. After
changing a model, generate + apply the next one:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
alembic current          # show the applied revision
```

`seed_db` also calls `metadata.create_all` (checkfirst) so it can stand up a schema on
its own for quick local use; with Alembic in play that call is a harmless no-op.

> The high-volume tables (`raw_*`, `ledger_entries`, `audit_log`) are created as
> `PARTITION BY RANGE` parents (the migration renders `postgresql_partition_by`). For
> production, manage monthly partitions with `pg_partman` (DB-SCHEMA §10).

## Tests

```bash
pytest            # async httpx smoke tests against the ASGI app (seed mode)
```

## Layout

```
app/
  core/      config (pydantic-settings), security (JWT/argon2), logging
  db/        async engine + session (lazy), declarative base
  models/    SQLAlchemy 2.0 ORM (users, connections, ingestion, emission, …)
  schemas/   Pydantic v2 (CamelModel → camelCase JSON matching the TS client)
  services/  seed fixtures + dashboard read services
  api/v1/    routers: auth, connections, ingest, footprint, recommendations,
             community, privacy, health
  main.py    app factory: CORS, OpenAPI, lifespan
alembic/     migration environment (async)
tests/       pytest + httpx
```
