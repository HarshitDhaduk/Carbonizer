# Deploying Carbonizer

Step-by-step guide for the free-tier stack:

* **Database** — [Neon](https://neon.tech) (serverless Postgres, free tier ≈ 1 GB).
* **Backend** — [Render](https://render.com) (Docker, free tier ≈ 15 min idle → cold-start).
* **Frontend** — [Vercel](https://vercel.com) (Next.js, free tier; static + on-demand SSR).

Total wall-clock to a live deployment, end-to-end: **~45 minutes** if it's
your first time touching these services, **~15 minutes** if you've done it
before. The artifacts (`render.yaml`, `frontend/vercel.json`, backend
`Dockerfile`) are all committed; this guide is the click-through to wire
them up.

> ⚠️ **Generate your secrets first** (Step 1). The deploy will reject
> defaults at startup — that's `Settings._assert_no_defaults_in_production`
> doing its job, not a bug.

## 0 — Prerequisites

* A GitHub account that owns this repo (Render + Vercel deploy from GitHub).
* `python` + `openssl` locally for secret generation.
* About 45 minutes of focused attention; less if you parallelise the three
  service signups in tabs.

## 1 — Generate production secrets

Three values you need to mint **before** you click anything in the dashboards.
Save them somewhere a password manager can hold them (1Password / Bitwarden /
the local Mac Keychain) — they only show in the Render dashboard once after
paste.

```bash
# SECRET_KEY — signs JWTs. 32-byte random hex.
openssl rand -hex 32

# ENCRYPTION_KEY — envelope-encrypts provider tokens (Phase 2.8).
# Fernet format: 32-byte url-safe base64.
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# DEMO_PASSWORD — the seed-mode demo user's password. Pick something
# at least 12 chars, mixed case + digits.
python -c "import secrets, string; alphabet = string.ascii_letters + string.digits; print(''.join(secrets.choice(alphabet) for _ in range(20)))"
```

You'll paste these into Render dashboard env vars in Step 3.

## 2 — Provision the database (Neon)

1. Sign up at [neon.tech](https://neon.tech). Email or GitHub OAuth.
2. **New Project** → name `carbonizer`, region `US East` (matches Render's
   default region for low latency).
3. After provisioning, the dashboard shows a connection string in the format:

   ```
   postgresql://USER:PASS@HOST/DB?sslmode=require
   ```

4. **Convert it to the async driver**: SQLAlchemy needs `+asyncpg`. Replace
   the scheme:

   ```
   postgresql+asyncpg://USER:PASS@HOST/DB?sslmode=require
   ```

   ⚠️ Keep `?sslmode=require` — Neon requires TLS.

5. Save this connection string. You'll paste it into Render in Step 3.

> 💡 **Pooling.** Neon has built-in connection pooling. The pool URL ends
> in `-pooler.neon.tech`. Use the **direct** (non-pooler) URL for Render
> because our app pools internally (`pool_size=10, max_overflow=20`,
> Phase 4.3). Stacking pools on pools wastes connections.

## 3 — Deploy the backend (Render)

The repo carries [`render.yaml`](../render.yaml) at the root — Render reads
it and provisions the service for you. You just paste the secrets.

1. Sign in to [dashboard.render.com](https://dashboard.render.com).
2. **New** → **Blueprint** → connect this GitHub repo → select branch `main`.
3. Render shows the planned service from `render.yaml` (one web service,
   `carbonizer-api`, Docker runtime, free plan, oregon region). Confirm.
4. Render asks for the env vars that are `sync: false`. Paste:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the `postgresql+asyncpg://…?sslmode=require` from Step 2 |
   | `SECRET_KEY` | the hex from Step 1 |
   | `ENCRYPTION_KEY` | the Fernet key from Step 1 |
   | `CORS_ORIGINS` | leave blank for now — you don't know the Vercel URL yet. We'll come back. |
   | `DEMO_PASSWORD` | the strong password from Step 1 |

5. **Apply**. Render builds the Docker image, runs `alembic upgrade head` on
   first boot (in the `CMD` of the Dockerfile), and brings the service up
   on `https://carbonizer-api.onrender.com` (your subdomain will vary).

6. **Verify**:

   ```bash
   curl -i https://YOUR-API.onrender.com/api/v1/healthz
   # → 200, {"status":"ok"}

   curl -i https://YOUR-API.onrender.com/api/v1/readyz
   # → 200, {"status":"ok","database":true}
   ```

   If `/readyz` returns 503 with `{"database":"error: …"}`, the most
   common cause is forgetting the `+asyncpg` driver scheme in `DATABASE_URL`.

## 4 — Deploy the frontend (Vercel)

1. Sign in to [vercel.com/new](https://vercel.com/new).
2. **Import Git Repository** → pick this repo.
3. Vercel detects Next.js automatically. Override **Root Directory** to
   `frontend/`. Leave Build / Output / Install commands at the
   `frontend/vercel.json` defaults (`npm run build`, `.next`, `npm ci`).
4. **Environment Variables**: add one.

   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://YOUR-API.onrender.com/api/v1` |

5. **Deploy**. After ~2 minutes the build finishes and Vercel gives you a
   URL like `https://carbonizer.vercel.app`.

## 5 — Wire CORS back

Until you tell Render about the Vercel URL, the browser will block
cross-origin requests from Vercel to Render.

1. Vercel dashboard → your project → settings → **Domains**. Note both:
   * The default `carbonizer.vercel.app` (preview deployments)
   * Any custom domain you've added.

2. Render dashboard → `carbonizer-api` → **Environment** → set
   `CORS_ORIGINS` to:

   ```
   https://carbonizer.vercel.app,https://www.your-custom-domain.com
   ```

   (Comma-separated, no spaces, no trailing slash. The repo's
   [`core/config.py`](../backend/app/core/config.py) parses this verbatim.)

3. Render redeploys automatically (env-change triggers a rebuild). Takes
   ~3 minutes.

## 6 — Smoke-test live

Once both services are up and CORS is wired:

```bash
# Anonymous landing page renders
curl -s -o /dev/null -w "%{http_code}\n" https://carbonizer.vercel.app/
# → 200

# OpenAPI spec is served + your tags are populated
curl -s https://YOUR-API.onrender.com/api/v1/openapi.json \
  | python -c "import json, sys; d=json.load(sys.stdin); print(d['info']['title']); [print(t['name']) for t in d['openapi'].split() and d.get('tags',[])]"
```

Then in a browser:

1. Visit `https://carbonizer.vercel.app`.
2. Click **Open app**.
3. Switch to **Sign in** and use the demo creds (`demo@carbonizer.app` +
   the password you set in Step 1's `DEMO_PASSWORD`).
4. You should land on the dashboard with the demo summary.

If anything 5xx's, check Render's **Logs** tab — JSON ndjson lines are
indexable; filter for `level: ERROR` and `request_id: <id from the
response header>`.

## 7 — Optional polish

### Custom domain

Vercel → settings → **Domains** → add your domain. Vercel walks you
through the DNS records (`A` → `76.76.21.21` or `CNAME` →
`cname.vercel-dns.com`).

Don't forget to add the new origin to `CORS_ORIGINS` on Render.

### Keep the backend warm

Render's free tier sleeps after 15 min idle (~30 s cold-start on the next
request). Two options:

* **Upgrade to Starter** ($7/mo) — Render keeps the instance hot.
* **Cron ping**: hit `/api/v1/healthz` every 10 min from
  [cron-job.org](https://cron-job.org) (free). Costs nothing but means
  Render's free-tier compute-minutes drain faster.

### Schedule the DSR sweep

GDPR/DPDP erasure (Phase 2.7) needs the
`services/dsr.sweep_overdue_erasures` job to run on a cadence so jobs past
their 48 h grace actually purge. Render Cron Jobs ($1/mo) hits a script;
or use any external cron that can `curl` an admin-protected endpoint.
*(The endpoint is currently library-only — wire it up as a Phase 7
follow-up.)*

### Add Sentry / OpenTelemetry

Not required for first launch but cheap to add later:

* **Sentry**: install `sentry-sdk[fastapi]`, set `SENTRY_DSN` env var,
  call `sentry_sdk.init(dsn=settings.sentry_dsn, environment="production")`
  during `lifespan`.
* **OpenTelemetry**: `opentelemetry-instrumentation-fastapi`. Render
  forwards traces over OTLP to Grafana Cloud's free tier (50k spans/mo).

## Reference — environment variables

The full set, with their defaults from
[`core/config.py`](../backend/app/core/config.py):

| Var | Required | Default | Notes |
|---|---|---|---|
| `ENVIRONMENT` | yes | `development` | `production` enables HSTS + the default-secret rejection |
| `SECRET_KEY` | yes (prod) | dev sentinel | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | yes (prod) | derived from `SECRET_KEY` | Fernet key |
| `DATABASE_URL` | yes (prod) | dev sentinel | `postgresql+asyncpg://…?sslmode=require` |
| `USE_DB` | yes | `false` | `true` in prod |
| `CORS_ORIGINS` | yes (prod) | localhost | comma-separated |
| `DEMO_PASSWORD` | yes (prod) | `demo12345` (dev) | ≥ 12 chars, mixed case + digits |
| `LOG_FORMAT` | no | `text` on TTY, `json` otherwise | force `json` on Render |
| `ACCESS_TOKEN_TTL_MINUTES` | no | `15` | bump for less-friction sessions |
| `REFRESH_TOKEN_TTL_DAYS` | no | `30` | drop for stricter sessions |
| `RATE_LIMIT_STORAGE_URL` | no | `memory://` | set `redis://…` for multi-instance |
| `RATE_LIMIT_ENABLED` | no | `true` | `false` only for testing |

## Reference — file map

| File | Used by | What it does |
|---|---|---|
| [`render.yaml`](../render.yaml) | Render | Service spec — Docker, env-var keys, healthcheck path |
| [`backend/Dockerfile`](../backend/Dockerfile) | Render build | Multi-stage Python 3.11 slim, non-root, HEALTHCHECK |
| [`backend/.dockerignore`](../backend/.dockerignore) | Render build | Keeps the image lean (no .venv, tests, etc.) |
| [`frontend/vercel.json`](../frontend/vercel.json) | Vercel | Framework hint (Next.js), build/install commands, edge region |
| [`backend/.env.example`](../backend/.env.example) | local dev | Template for `.env` |
| [`backend/alembic/`](../backend/alembic/) | first deploy | `alembic upgrade head` runs on every container boot |
