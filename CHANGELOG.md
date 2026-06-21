# Changelog

All notable changes to Carbonizer are recorded here, following the spirit of
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and adhering to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). For the SRE-facing
release notes (runbook deltas, dependency CVE fixes, infra rotation), see
[`docs/RUNBOOK.md`](docs/RUNBOOK.md).

## [Unreleased]

### Added

- Production code-quality split — `services/dsr.py` (329 → 184) extracted the
  GDPR-export half into `services/dsr_export.py`; the on-boarding auth form
  extracted `PasswordField.tsx` and `auth-errors.ts` so `AuthGate.tsx` (266 →
  181) focuses on form state + submission.
- Property-based tests (Hypothesis) for `services/carbon.py` and
  `services/impute.py` — covers monotonicity in spend / grid intensity / bank
  hub signal, plus the R1 confidence-band contract.
- Three Playwright specs — `questionnaire.spec`, `keyboard-nav.spec`,
  `connect-source.spec` — landing-to-onboarding coverage now includes the
  questionnaire render, the skip-link → main focus jump, and the
  documented seed-mode 503 on `/connections/bank/link`.
- Top-level `CHANGELOG.md` (this file) + `CONTRIBUTING.md`.

### Changed

- Backend coverage floor lifted from 65% to 70% (live: 70.9% with `_export`
  split). CI's pytest step explicitly verifies the Docker daemon is reachable
  so testcontainers DB-mode tests can't silently downgrade to seed-mode-only.
- Frontend CI now runs `npm run test:coverage` (vitest with thresholds) — the
  un-gated `npm test` step is gone.

### Fixed

- Production cookies now `SameSite=None; Secure` so cross-site auth survives
  third-party-cookie blockers (Safari ITP, Brave, Firefox-strict). Defends
  the *.vercel.app frontend ↔ *.onrender.com API deploy pattern. CSRF
  double-submit remains the state-change gate.
- Vercel rewrite — `/api/v1/*` proxies to Render; the browser fetches
  same-origin and cookies are first-party to `vercel.app`. Resolves the
  register-201-then-/auth/me-401 repro on browsers with strict third-party
  cookie policy.
- CORS — `https://*.vercel.app` + `https://*.onrender.com` accepted by regex
  in production so preview URLs aren't gated on per-commit env-var edits.

## [0.1.0] — Pre-launch (Phases 1–7)

Initial production-ready release covering Phases 1 through 7 of
[`docs/IMPROVEMENT-PLAN.md`](docs/IMPROVEMENT-PLAN.md).

### Phase 7 — Production readiness

- Multi-stage backend `Dockerfile` (Python 3.11-slim → distroless-style
  runtime stage; non-root user `app:10001`; HEALTHCHECK against `/healthz`).
- Structured JSON logging — `core/logging.py` auto-selects ndjson when stdout
  isn't a TTY. `X-Request-Id` middleware propagates a UUID through every
  log line via a contextvar.
- Real `/readyz` returns 503 with a DB-error body when `SELECT 1` fails.
- `render.yaml` blueprint + `frontend/vercel.json` + `docs/DEPLOY.md`,
  `docs/RUNBOOK.md`, `docs/PRODUCTION-CHECKLIST.md`.

### Phase 6 — Code-quality polish

- `services/estimator.py` split into `questionnaire.py` (data + helpers) +
  `voi.py` (R0 scoring) + `estimator.py` (math); `bank_sync.py` extracted
  `_collect_spend` / `_collect_energy` / `_merge_categories` helpers from
  `recompute_footprint`.
- `useLogoutWithConfirm` hook collapses the `AccountMenu` ↔ `ProfileClient`
  duplicate.
- mypy --strict + ruff `C901` cyclomatic-complexity gates enabled.
- OpenAPI metadata + `summary=` / `description=` on every load-bearing route;
  `FootprintSummary` schema gets a realistic `json_schema_extra` example.
- 5 ADRs in `docs/adr/` (server-defined questionnaire, heuristics with ML
  seam, JWT in cookies, raw_* partitioning, sandbox provider design).

### Phase 5 — Accessibility

- SkipLink + route-change focus management in `AppPage`; `<main id="main">`
  on every shell.
- AuthGate form a11y — visible `*` is `aria-hidden`, `aria-required` /
  `aria-invalid` / `aria-describedby` wired; error summary at the top of
  the form is `role="alert"`.
- Keyboard-only plant flow on the 3D biome — `BiomeStore.plantRandom()` +
  Space / Enter handler + sibling "Plant a tree" button.
- Dark-theme contrast audit: every body / accent pair now ≥ 5.3:1.
  `--text-lo` bumped to `#8aa094`.
- E2E: dashboard (authed) a11y + dedicated color-contrast watchdog test.

### Phase 4 — Efficiency

- HTTP cache headers per route (private 60s on `/footprint/summary`, private
  300s on `/community/benchmark`, public-immutable + ETag on
  `/onboarding/questions`).
- Connection pool tuned: `pool_size=10, max_overflow=20, pool_recycle=1800`;
  `/metrics` exposes the default prometheus_client registry; GZip on JSON
  bodies > 1KB.
- TanStack Query refactor — Dashboard / Insights / Act / Profile + the
  ConnectSources mutation; ~150 lines of effect-fetch removed.
- Bundle analyzer (`ANALYZE=true npm run analyze`) + Lighthouse CI in a
  separate job.

### Phase 3 — Testing

- vitest + Testing Library + jsdom (33 unit tests on lib/, ui/, store/).
- Hypothesis property-based tests for the estimator (6 invariants × 200
  examples).
- testcontainers Postgres 16 — 8 DB-mode integration tests covering register,
  login, recompute, R1 imputation, meter promotion, idempotency.
- Playwright + `@axe-core/playwright` — cookie+CSRF auth flow, landing +
  onboarding a11y.
- mutmut weekly cron on the pure-math services.

### Phase 2 — Security hardening

- JWT in `HttpOnly` cookies + double-submit CSRF (was localStorage).
- slowapi rate limiting: 5/min on `/auth/login`, 3/hour on `/auth/register`,
  120/min on `/onboarding/progress`.
- Hard-fail on default secrets in production (`Settings._assert_no_defaults`).
- Defensive security headers + HSTS in production.
- 12-char password minimum + breach-list substring check + email-in-password
  rejection.
- Audit log writer on every auth / connection / DSR event.
- Envelope encryption for `connections.access_token_enc` via Fernet.
- pip-audit + npm audit weekly in CI.

### Phase 1 — CI quality gates

- ruff + mypy + pytest + dependabot grouped weekly + prettier + ESLint.

[Unreleased]: https://github.com/HarshitDhaduk/Carbonizer/compare/main...HEAD
[0.1.0]: https://github.com/HarshitDhaduk/Carbonizer/releases/tag/v0.1.0
