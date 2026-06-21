# Carbonizer — Operations Runbook

What to do when something burns. Each section is structured the same way:

* **Signal** — the alert / symptom you noticed.
* **Triage** — first 60 seconds of "is this actually broken?"
* **Mitigation** — stop the bleeding.
* **Resolution** — fix the underlying cause.
* **Postmortem** — what to capture so it doesn't recur.

Keep this terse. A wall of caveats helps no one at 3am.

---

## 1. Database is unreachable

### Signal

* `/api/v1/readyz` returns 503 with `{"database":"error: …"}`.
* Render's "Health Check" tab goes red; traffic stops landing on this
  instance.
* Logs spike with `asyncpg.PostgresConnectionError` or
  `sqlalchemy.exc.OperationalError`.

### Triage

```bash
# Is the API alive at all (process-level)?
curl -s -o /dev/null -w "%{http_code}\n" https://YOUR-API.onrender.com/api/v1/healthz
# 200 → process up, DB-side fault
# 502/503/timeout → process down, restart it from Render's dashboard
```

Then check Neon status:

* [neon.tech/status](https://neon.tech/status) — platform-level outage.
* Neon dashboard → your project → **Compute** tab. The branch may be
  *suspended* (free-tier auto-suspends after 5 min idle) or *unavailable*.

### Mitigation

* If Neon is suspended, the **next request wakes it**; first request
  takes ~5 seconds. Nothing to do.
* If Neon is platform-down: post status in your support channel. No
  action will help; wait for Neon to recover. The app surfaces 503s
  cleanly — no data loss, just unavailability.
* If the connection pool is exhausted (look for `QueuePool limit … reached`),
  bounce the Render instance: dashboard → **Manual Deploy** → **Clear
  build cache & deploy**. New instance, fresh pool.

### Resolution

* Find the cause class:
  * **Pool exhaustion** → a route is leaking sessions. Search
    [`backend/app/services/`](../backend/app/services/) for any `await
    db.execute(…)` not under `async with sessionmaker() as session`.
    The FastAPI `get_db` dependency yields once per request and the
    framework closes it — direct engine use bypasses that.
  * **Connection refused** → `DATABASE_URL` env var on Render is wrong
    or expired. Rotate via Neon (Settings → **Reset Password**) and
    update Render env.
  * **TLS failure** (`SSL connection has been closed unexpectedly`) →
    the `?sslmode=require` query string was dropped. Re-paste the
    URL with the suffix.

### Postmortem

* Add a regression test in
  [`backend/tests/test_db_mode.py`](../backend/tests/test_db_mode.py)
  that reproduces the leak pattern (e.g. a route calling a service that
  spawns a second session under the same request).
* If Neon's free tier auto-suspend caused user-facing 5xx: upgrade to a
  paid tier or wire a 10-min cron ping to keep it warm.

---

## 2. Runaway recompute pegs CPU

### Signal

* Render's CPU graph hits 100% and stays there.
* p95 latency on `/api/v1/footprint/summary` climbs above 2 s.
* Lots of consecutive `services.bank_sync.recompute_footprint` lines in
  the logs.

### Triage

```bash
# How many recompute calls are in flight? Filter the structured JSON.
# (On Render's Logs tab; or pipe to jq locally if you've downloaded a chunk.)
# Look for: msg ~= "recompute" AND no matching "recompute done" within 30s.
```

The most common cause is a **bank sync loop** — a sync call that triggers
a recompute that triggers another sync (the FE retries on every error).

### Mitigation

1. Drain traffic from this instance: Render → **Manual Deploy** to spawn
   a new one and route to it. Old instance gets one request in flight
   max while it finishes.
2. If clients are spinning, disable the connect flow temporarily by
   editing `CORS_ORIGINS` on Render to an empty value — every connect
   call 5xx's, the FE backs off. (Crude but effective for the 60-second
   window you need.)

### Resolution

* The recompute is **idempotent**; running it twice for the same user
  doesn't double-count (ON CONFLICT DO NOTHING on the raw_ tables).
  But it's expensive. Add a Redis-backed lock per `user_id` if multi-
  instance: only one recompute may run per user at a time.
* Reduce the WINDOW_DAYS the recompute scans (currently set in
  [`services/bank_sync.py`](../backend/app/services/bank_sync.py)) — the
  scan is bounded, but for a user with months of history it isn't bounded
  *enough*.

### Postmortem

* Did `/metrics` (Prometheus scrape) catch the spike? If not, the
  process-level RSS metric isn't enough — wire per-handler latency
  histograms (the
  `prometheus-fastapi-instrumentator` ↔ FastAPI 0.138 compat issue
  documented in [main.py](../backend/app/main.py)).

---

## 3. A secret has leaked

### Signal

* GitHub secret scanning email, an internal report, or "did anyone
  commit `.env`?".
* If it's `SECRET_KEY`: existing JWTs are forge-able. Bad.
* If it's `ENCRYPTION_KEY`: an attacker who can read the DB can also
  decrypt stored provider tokens.
* If it's `DEMO_PASSWORD`: probably nothing real — the demo account has
  no data, but treat as compromised anyway.

### Triage

```bash
# Confirm the leak first — don't rotate based on a maybe.
gh secret-scanning alerts list --repo YOUR-ORG/Carbonizer
# Or grep history if it's a self-report:
git log -p -- backend/.env
```

### Mitigation

1. **Rotate the affected secret immediately** in the Render dashboard
   → Environment → edit value → Save. Render redeploys; new instance
   has the new secret.
2. If `SECRET_KEY` rotated: every existing JWT now decodes invalid.
   Users get bounced to `/onboarding` on their next request and have to
   sign in again. The audit log (`auth.logout` rows) won't fire because
   the access cookie is unreadable. That's OK — the password hash check
   still pins identity.
3. If `ENCRYPTION_KEY` rotated: existing rows in `connections.access_
   token_enc` are now unreadable. The recompute *quietly skips* tokens
   that fail decryption (`InvalidToken` is logged but not crashed —
   intentional per `core/crypto.py` docstring). Users will need to
   re-link their sources to repopulate the tokens.

### Resolution

* Rotate downstream provider tokens too if a bank / meter token was
  leaked. The encrypted ones are useless once `ENCRYPTION_KEY`
  changes, but **already-decrypted-in-memory** ones may be in attacker
  logs. Treat as compromised.
* Audit the audit log
  ([`models/privacy.py:AuditLog`](../backend/app/models/privacy.py)) for
  `auth.login.success` rows between the leak window — anyone who logged
  in using a forged JWT will show up if you cross-reference IPs.

### Postmortem

* Why was the secret committable in the first place? Add the leaked
  path to `.gitignore` if missing, and to the pre-commit hook
  (`.github/workflows/ci.yml` already has `pip-audit` + `npm audit`,
  but no secret scanner yet).
* GitHub's push-protection rule for known secret formats is free;
  enable it in repo settings.

---

## 4. Refresh tokens expire en masse

### Signal

* Users report being signed out unexpectedly.
* `/api/v1/auth/refresh` 401-rate spikes in the logs.
* `audit_log` shows `auth.login.success` rows from the same users you'd
  expect to be already-signed-in.

### Triage

* The refresh JWT is 30 days (`settings.refresh_token_ttl_days`). If the
  service has been live > 30 days and a cohort signed up in the same
  week, they all expire in the same window.
* Bigger concern: did you **rotate `SECRET_KEY`** in the last 24h? Every
  cookie is invalid then (see #3).

### Mitigation

* Communicate: post a status banner. It's annoying for users but not
  a data integrity issue.
* Confirm the refresh endpoint itself is healthy:

  ```bash
  curl -i https://YOUR-API.onrender.com/api/v1/auth/refresh
  # → 401 with body {"detail":"Not authenticated"} when no cookie
  # → 500 = the endpoint itself is broken; deploy revert
  ```

### Resolution

* If it's the rolling-cohort expiry: nothing to do except let users
  sign back in.
* If it's an outage cause: bump `REFRESH_TOKEN_TTL_DAYS` in the env to
  something like `60` to widen the future expiry distribution. Don't
  drop below `7` even briefly — it forces re-login storms.

### Postmortem

* Add a **scheduled metric**: cookie cohort age distribution. The
  Prometheus scrape doesn't carry user-scoped data today, but a daily
  cron query against `audit_log` can emit a gauge for "refresh tokens
  expiring in the next 7 days".

---

## 5. A mass DSR job arrives

### Signal

* `audit_log` shows `privacy.export.request` or `privacy.erase.request`
  rows from a sudden cluster of users (regulator action, public concern,
  press cycle).
* `dsr_jobs` table balloons.

### Triage

```sql
-- How many pending erase jobs are within the 48h grace window right now?
SELECT count(*) FROM dsr_jobs
WHERE kind = 'erase' AND status = 'pending'
  AND scheduled_purge_at > now();

-- How many overdue (the sweep should be eating these)?
SELECT count(*) FROM dsr_jobs
WHERE kind = 'erase' AND status = 'pending'
  AND scheduled_purge_at <= now();
```

If the second query is non-zero and rising, the sweep isn't running.

### Mitigation

* For **export** jobs: they're synchronous from the user's POV — they
  hit `/privacy/export/{id}/download` and we stream. If the DB is
  swamped, the request 504s and the user retries. Nothing to do beyond
  the platform-level "DB up, recompute drained" steps above.
* For **erase** jobs: the 48h grace window is the budget. If the sweep
  has been down for *more* than 48h, you've missed the regulatory SLA —
  call legal.

### Resolution

* Confirm the sweep is wired. The function
  [`services.dsr.sweep_overdue_erasures`](../backend/app/services/dsr.py)
  is library-only today — production needs to call it on a cron.
  Render Cron Jobs ($1/mo) or any external cron hitting an admin
  endpoint works.
* If you're running it on cron and it's failing: check the Render Cron
  Jobs logs. The sweep is wrapped in `try/except` per job — one bad row
  doesn't stop the others, but the failure shows up in the JSON log
  with `level: warning` and `msg: "DSR sweep failed for user=…"`.

### Postmortem

* Wire the sweep into a Render Cron Job + write a runbook entry above
  pointing here.
* `dsr_jobs` is unpartitioned today. If volume gets serious (>1M rows),
  partition by month on `requested_at` — same migration pattern as
  `raw_*`.
