# Carbonizer — Security Review

A self-review against OWASP Top 10 (2021) + the project's specific risks. This
doc lists what's in place after Phase 2 of [IMPROVEMENT-PLAN.md](IMPROVEMENT-PLAN.md)
and what remains for Phase 2 follow-ups (cookies + CSRF + GDPR DSRs).

> A green tick means the control is implemented **and tested**. A yellow `~`
> means partial (e.g. middleware in place but not yet fingerprinted in CI).
> A red `✗` is a known gap with an owner and a target phase.

## OWASP Top 10 (2021)

| # | Category | Status | Where |
|---|---|---|---|
| A01 | Broken Access Control | ✅ | All routes use `Depends(require_user)` / `get_optional_user`. JWT subject validated against UUID. `/auth/me` returns 404 on subject mismatch. |
| A02 | Cryptographic Failures | ✅ | **Argon2id** for passwords ([core/security.py](../backend/app/core/security.py)). JWT signed HS256 with rotating key. **Envelope encryption (Fernet)** for `connections.access_token_enc` via [core/crypto.py](../backend/app/core/crypto.py); production refuses to boot without `ENCRYPTION_KEY`. |
| A03 | Injection | ✅ | SQLAlchemy ORM exclusively; no raw SQL string concatenation. Pydantic v2 validates every input. |
| A04 | Insecure Design | ✅ | Privacy-by-design through the data model (k-anonymity on cohorts, partitioned `raw_*` for retention drops). |
| A05 | Security Misconfiguration | ✅ | **Hard-fail in production** on default `SECRET_KEY` / `DATABASE_URL` / `DEMO_PASSWORD` ([core/config.py](../backend/app/core/config.py)). **Security headers middleware** ([core/security_headers.py](../backend/app/core/security_headers.py)) sets X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, COOP, CORP, CSP (API). **HSTS** in production only. |
| A06 | Vulnerable Components | ✅ | **`pip-audit`** (backend) + **`npm audit --audit-level=high`** (frontend) run in CI on every PR. Dependabot weekly with grouped PRs to avoid peer-dep conflicts. |
| A07 | Identity & Auth Failures | ✅ | **Rate limiting** on `/auth/login` (5/min), `/auth/register` (3/hour), `/onboarding/progress` (120/min) via slowapi. **Stronger password policy** ([schemas/auth.py](../backend/app/schemas/auth.py)) — 12-char minimum, weak-password list, email-in-password rejected, all-letters/all-digits rejected. **JWT lives in `HttpOnly` cookies** with `SameSite=Lax` + double-submit CSRF token ([core/csrf.py](../backend/app/core/csrf.py)); localStorage tokens are gone. |
| A08 | Software & Data Integrity | ✅ | Idempotent ingestion via `ON CONFLICT DO NOTHING` on natural keys. Footprint snapshot is regenerable from raw data + factors. |
| A09 | Security Logging & Monitoring | ✅ | **Audit log writer** ([services/audit.py](../backend/app/services/audit.py)) wired to auth events (register/login/logout), connection link/sync/disconnect, and privacy DSR events (request/download/cancel); partitioned `audit_log` table ready for 1-year retention. |
| A10 | SSRF | ✅ | Backend doesn't fetch user-supplied URLs (sandbox providers are deterministic synthetic data). |

## Carbonizer-specific risks

| Risk | Mitigation | Status |
|---|---|---|
| **JWT exfil via XSS** (localStorage) | `HttpOnly` cookies + CSRF double-submit ([core/csrf.py](../backend/app/core/csrf.py)) | ✅ |
| **Default secrets leak to prod** | `model_validator` raises `InsecureProductionConfigError` at startup | ✅ |
| **Credential stuffing / brute force** | slowapi (5/min/IP login + 20/hr/email); 429 with Retry-After | ✅ |
| **Cohort de-anonymization** | k-anonymity threshold k=50 + Laplace DP on cohort mean | ✅ |
| **Cross-replica rate-limit bypass** on multi-instance deploys | `RATE_LIMIT_STORAGE_URL=redis://…` shared backend | docs only (free-tier is single-instance) |
| **CSP bypass via injected scripts** in /docs Swagger UI | CSP intentionally not applied to /docs (Swagger needs inline scripts from a CDN) | accepted risk on staging; remove `/docs` route in production |
| **Audit-log loss** if DB write fails | `audit.record()` catches and warns; never crashes the request | ✅ |
| **Mass-assignment via CamelModel** | Pydantic v2 ignores unknown fields by default | ✅ |

## Verified behaviours (Phase 2 tests)

From [`tests/test_api.py`](../backend/tests/test_api.py):

- `test_security_headers_present` — every response carries the defensive set.
- `test_password_policy_min_length` — 11 chars rejected.
- `test_password_policy_rejects_weak` — `password123!` / `letmein-now-1` / `Carbonizer123` all rejected via substring match against the weak list.
- `test_password_policy_rejects_email_in_password` — `alice` in password for `alice@example.com` rejected.
- `test_password_policy_accepts_strong` — `r4nd0m-words-xyz` accepted.
- `test_production_hard_fails_on_default_secret` — `Settings(environment="production", secret_key=DEFAULT_SECRET_KEY, …)` raises `InsecureProductionConfigError`.
- `test_production_accepts_real_secret` — production config with real values boots cleanly.
- `test_login_rate_limit_fires` — 6th login attempt within a minute returns 429 with `Retry-After`.
- `test_audit_record_seed_mode_is_noop` — audit writer never crashes the request, even with `db=None`.

## Phase 2 — complete

All Phase 2 items in [IMPROVEMENT-PLAN.md](IMPROVEMENT-PLAN.md) are now landed.
The follow-ups that were deferred in the first drop have all shipped:

* **Phase 2.1 — JWT → HttpOnly cookies + CSRF** — `affbaba`. Cookies set on
  `/auth/login`, `/auth/register`, `/auth/refresh`; `/auth/logout` clears them;
  double-submit CSRF on every state-changing route; frontend `client-api.ts`
  uses `credentials: "include"` and echoes the `cb_csrf` cookie in
  `X-CSRF-Token`.
* **Phase 2.7 — GDPR / DPDP data-rights handlers** — `0708829`. Real
  `/privacy/export` (recorded as a `DsrJob`, bundle streamed by
  `/privacy/export/{id}/download`), `/privacy/erase` with a 48-h grace, and
  `/privacy/erase/{id}/cancel`. The sweep service purges overdue rows;
  production deploys point a cron at it.
* **Phase 2.8 — Envelope encryption** — `0708829`. Fernet (`core/crypto.py`)
  wraps every write to `connections.access_token_enc`; production refuses to
  boot without an explicit `ENCRYPTION_KEY`. The sandbox link flow exercises
  the encryption path with a placeholder token so the prod swap-in doesn't
  introduce an untested code path.
* **Audit log wiring** — `0708829`. Connection link/sync/disconnect and
  privacy DSR events all write to `audit_log` via the existing
  `audit.record` service.
