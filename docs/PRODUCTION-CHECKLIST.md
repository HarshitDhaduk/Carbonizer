# Production checklist

Sign off **before** flipping a deploy from `development` to `production`
traffic. Each line either holds or it doesn't; "kinda" is a no.

> 💡 Reading order: top-to-bottom on the first deploy; reverse-chrono
> (latest section first) for a re-check before a sensitive change.

## A — Secrets + identity

- [ ] `SECRET_KEY` is `openssl rand -hex 32`, not the dev default.
- [ ] `ENCRYPTION_KEY` is a freshly-generated Fernet key, not derived
  from `SECRET_KEY`. (`core/crypto.py` refuses to boot without it
  in production — verify by tailing the first deploy log.)
- [ ] `DEMO_PASSWORD` is ≥ 12 chars, mixed case + digits, and not
  the default `demo12345`.
- [ ] The Render dashboard env vars are saved with sync: false so they
  don't echo back to the repo's `render.yaml`.
- [ ] No `.env` file is committed; `git log -p -- .env` is silent.
- [ ] GitHub push-protection is enabled on the repo (Settings →
  Security → Secret scanning).

## B — Database + persistence

- [ ] `DATABASE_URL` uses `postgresql+asyncpg://` (the async driver
  scheme), not `postgresql://` (sync default).
- [ ] `?sslmode=require` is in the URL; the Neon dashboard's "Use
  pooled connection" toggle is **off** for this URL (our app pools
  internally — Phase 4.3).
- [ ] First request after deploy returns 200 on
  `/api/v1/readyz` with `{"database": true}`.
- [ ] `alembic upgrade head` ran successfully on first boot (check the
  Render logs — line starts with `INFO  [alembic.runtime.migration]
  Running upgrade …`).
- [ ] Default partitions exist for each `raw_*` + `audit_log` + `ledger_
  entries` table — verify via psql:

  ```sql
  SELECT inhrelid::regclass FROM pg_inherits
  WHERE inhparent IN ('raw_transactions'::regclass, 'audit_log'::regclass);
  ```

- [ ] A backup is scheduled. Neon's free tier carries 7 days of point-
  in-time recovery automatically; bigger plans need a `pg_dump` cron.

## C — Networking + CORS

- [ ] `CORS_ORIGINS` on Render lists every domain the frontend serves
  from (Vercel default + custom domain). Comma-separated, no spaces,
  no trailing slash.
- [ ] Frontend can fetch `/api/v1/auth/me` without a CORS preflight
  failure. Browser devtools → Network tab → should be 401 (no
  cookie) not "CORS error".
- [ ] Cookies set by `/auth/login` carry `Secure`, `HttpOnly` (access
  + refresh), and `SameSite=Lax`. Inspect in browser devtools →
  Application → Cookies after a real login.
- [ ] The frontend's `NEXT_PUBLIC_API_BASE_URL` ends in `/api/v1` and
  is `https://`, not `http://`.

## D — Observability + alerts

- [ ] Logs are ndjson (`LOG_FORMAT=json` env var). Spot-check a few
  Render log lines — they should `json.loads()` cleanly.
- [ ] `request_id` appears in every error log line. Grep one user's
  bug-report id in Render Logs and confirm you can trace it.
- [ ] `/metrics` is reachable. (Free-tier Render doesn't scrape this
  for you; Grafana Cloud Free or self-hosted Prometheus will.)
- [ ] An alert exists for "5xx rate > 1% for 10 minutes". Set in
  Render → Notifications, or via UptimeRobot / Better Stack.

## E — Security headers + auth

- [ ] HSTS header on every response (`max-age=63072000; includeSubDomains; preload`).
  Verify with `curl -I https://YOUR-API.onrender.com/`.
- [ ] CSP header on JSON responses includes `default-src 'none'`.
- [ ] `/docs` is reachable for tooling but you're aware it's a Swagger
  UI public surface. For a private production deploy: gate it behind
  basic auth or remove the route in `main.py`.
- [ ] Rate limiting fires: `for i in 1..6 do curl … /auth/login; done`
  hits a 429 with `Retry-After`.
- [ ] The first response after deploy carries a fresh ETag on
  `/api/v1/onboarding/questions`; a follow-up with `If-None-Match` gets
  a 304.

## F — Acceptance + tests

- [ ] CI is green on `main` for backend + frontend + e2e jobs.
- [ ] `npm run lhci` against the live deploy clears the Lighthouse
  budget (performance is currently soft-gated; LCP/CLS are hard).
- [ ] Backend mypy `--strict` is the configured gate (already true post
  Phase 6.4 — verify the CI run).
- [ ] No file > 250 lines except the documented exceptions
  (dsr.py 329, auth.py 271, AuthGate.tsx 266, bank_sync.py 280).

## G — Operational

- [ ] [`docs/RUNBOOK.md`](RUNBOOK.md) is in the on-call slack channel
  or pinned in your incident-management tool.
- [ ] The DSR sweep cron is wired (Render Cron Job, or external) —
  `services.dsr.sweep_overdue_erasures` runs at least every 6h so a
  user's 48h grace window is always honoured to within margins.
- [ ] Cold-start latency budget: Render free tier sleeps after 15 min.
  If user-facing, upgrade to Starter ($7/mo) or wire a 10 min ping
  from cron-job.org.
- [ ] An incident channel exists (Slack / Discord / Telegram). The
  on-call person knows to look at:
  1. Render dashboard → Logs (filter for `level: error`)
  2. Neon dashboard → Compute → status
  3. Vercel dashboard → Deployments → most recent

## H — Compliance

- [ ] [`docs/SECURITY-REVIEW.md`](SECURITY-REVIEW.md) is current —
  re-read the OWASP table, ensure every "✅" still reflects reality.
- [ ] [`docs/A11Y-REPORT.md`](A11Y-REPORT.md) is current — re-read,
  flag any "_todo_" walkthrough steps that should be filled before
  launching to a broader audience.
- [ ] The GDPR/DPDP data-rights endpoints work end-to-end:
  1. `POST /privacy/export` → 202 with a `dsr_job` id
  2. `GET /privacy/export/{id}/download` → streams a JSON bundle
  3. `POST /privacy/erase` → 202 with a `scheduledPurgeAt` 48h away
  4. `POST /privacy/erase/{id}/cancel` → 200, status flips to `failed`
     (we repurpose `failed` as "cancelled" — see the dsr.py docstring).

---

If every box is ticked: ship it. If three or more are open: don't.
