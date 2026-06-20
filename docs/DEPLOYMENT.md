# Carbonizer — Free-Tier Deployment

Live deployment of the full stack on three free services that all
auto-deploy from this repo:

| Layer | Service | What's free | Caveat |
|---|---|---|---|
| **Frontend** (Next.js) | [Vercel](https://vercel.com) | Hobby tier — unlimited static, 100 GB bandwidth/mo | None for this size |
| **Backend** (FastAPI) | [Render](https://render.com) | Free Web Service — 750 hrs/mo Docker | **Sleeps after 15 min idle**, ~30 s cold start |
| **Database** (Postgres 16) | [Neon](https://neon.tech) | Free Postgres — 0.5 GB, autosuspend | None for this size |

Total cost: **£0**. Demo-grade — fine for a hackathon, screenshots, or a
showcase URL. Trade off the 30-second cold start on the backend and you're
done.

---

## Prerequisites

A GitHub account that owns this repo and accounts on Vercel, Render, and
Neon (all sign-in-with-GitHub).

---

## 1. Provision the database (Neon)

1. https://console.neon.tech → **New Project** → name it `carbonizer`,
   region close to your Render region (`Oregon (US West)` matches the
   default in `render.yaml`).
2. After it spins up, copy the **connection string**. You want the
   `psql` one but **append the asyncpg driver**:

   ```
   # Neon gives you something like:
   postgresql://user:pass@ep-xxx.us-west-2.aws.neon.tech/neondb?sslmode=require

   # SQLAlchemy/asyncpg need:
   postgresql+asyncpg://user:pass@ep-xxx.us-west-2.aws.neon.tech/neondb?ssl=require
   ```

   Notes:
   - `postgresql` → `postgresql+asyncpg` (driver suffix).
   - `?sslmode=require` → `?ssl=require` (asyncpg uses a different param name).

3. Keep this string — you'll paste it into Render in the next step.

> **Why Neon, not Render Postgres?** Render's free Postgres expires after 90
> days. Neon is free with no expiration; it auto-suspends after 5 min idle
> but resumes in ~300 ms — barely noticeable.

---

## 2. Deploy the backend (Render)

The `render.yaml` blueprint at the repo root configures everything.

1. https://dashboard.render.com → **New + → Blueprint**.
2. Connect your GitHub account and pick the `Carbonizer` repo.
3. Render reads `render.yaml`, shows a preview of the `carbonizer-api`
   web service, and asks for the **sync: false** env vars:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the Neon string from step 1 (with `+asyncpg` and `?ssl=require`) |
   | `SECRET_KEY` | `openssl rand -hex 32` |
   | `CORS_ORIGINS` | put `https://placeholder.vercel.app` for now — we'll update it in step 4 |
   | `DEMO_PASSWORD` | `demo12345` (or any value) |

4. **Apply**. Render builds the Docker image, runs `alembic upgrade head`
   on the container's startup command, then serves `uvicorn`.
5. After ~5 min the service is live at something like
   `https://carbonizer-api.onrender.com`. Verify:

   ```bash
   curl https://carbonizer-api.onrender.com/api/v1/healthz
   # → {"status":"ok"}
   ```

6. **Seed the demo user** (one-off, via the Render dashboard
   "Shell" tab on the service):

   ```bash
   python -m app.db.seed_db
   ```

---

## 3. Deploy the frontend (Vercel)

1. https://vercel.com/new → **Import** the GitHub repo.
2. **Root Directory**: `frontend` (Vercel's auto-detect should pick this
   from `vercel.json`).
3. **Environment Variables**:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://carbonizer-api.onrender.com/api/v1` |

4. **Deploy**. Vercel runs `npm ci && npm run build`. Live in ~2 min at
   `https://carbonizer-<your-id>.vercel.app`.

---

## 4. Close the CORS loop

Go back to Render dashboard → `carbonizer-api` → **Environment** →
update `CORS_ORIGINS` to the actual Vercel URL:

```
CORS_ORIGINS=https://carbonizer-<your-id>.vercel.app
```

Render redeploys automatically. The browser can now talk to the API.

---

## 5. Smoke-test

Open the Vercel URL → click **"Sign in"** → log in as
`demo@carbonizer.app` / `demo12345`.

If the dashboard hangs at "Loading…" for ~30 s on the first hit, that's
Render's free-tier cold start. Subsequent requests are fast.

---

## Continuous deploys

After this one-time setup, **every push to `main` deploys automatically**:

- Vercel rebuilds the frontend on any change under `frontend/`.
- Render rebuilds the backend on any change under `backend/`.
- Neon does nothing — it just stores the data.

PRs from feature branches get **Vercel preview URLs** automatically. Render
optionally supports preview environments on a paid plan.

---

## Notes & alternatives

- **`uv.example.log` etc.** are gitignored, so nothing leaks at build time.
- **`backend/.env` is gitignored** — production secrets live only in
  Render's dashboard.
- **If you outgrow Render's 750 hr/mo or the cold-start hurts**, the
  cheapest paid option is Render's `Starter` plan (\~£5/mo) which keeps the
  service warm. Fly.io's free tier (`shared-cpu-1x`) is another route but
  needs a credit card on file.
- **If Vercel ever becomes an issue**, the same Next.js build runs on
  Cloudflare Pages free tier.
- **Custom domain**: both Vercel and Render let you attach one on the free
  tier (Vercel handles HTTPS automatically; Render requires the DNS CNAME +
  verification flow).
