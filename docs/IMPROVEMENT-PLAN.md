# Carbonizer — 7.2 → 10 / 10 Implementation Plan

Concrete, ordered, effort-estimated plan to take the MVP from "honest hackathon
submission" (current state) to "would pass an external code review,
security audit, and WCAG 2.1 AA conformance audit by a senior engineer who
didn't write it." Companion to [SELF-EVALUATION](#) and grounded in the gaps
called out in the README.

> **What 10/10 actually means.** For each area we adopt a *bar that an external
> auditor would sign off on*, not a self-graded one. That's why some items
> (CI, security headers, axe-core in CI) are non-negotiable — they're the
> objective evidence the score is real.

## Headline summary

| # | Phase | Days | Lifts | Status |
|---|---|---|---|---|
| 1 | **CI + quality gates** | 1–2 | Foundation. Locks everything else in. | ✅ done |
| 2 | **Security hardening** | 3–5 | Security 6 → 10 | ~ in progress (2.2/2.3/2.4/2.5/2.6/2.9 done; 2.1 cookies + 2.7/2.8 left) |
| 3 | **Test coverage (frontend + DB-mode + E2E)** | 4–6 | Testing 6 → 10 | ⬜ |
| 4 | **Efficiency polish (cache + bundle + pool)** | 2–3 | Efficiency 8 → 10 | ⬜ |
| 5 | **WCAG 2.1 AA + screen-reader pass** | 2–3 | Accessibility 8 → 10 | ⬜ |
| 6 | **Code-quality polish + module splits + ADRs** | 1–2 | Code Quality 8 → 10 | ⬜ |
| 7 | **Production readiness (bonus)** | 3–5 | Deploy-ready | ⬜ |
| **Total** | one engineer end-to-end | **16–26 days** | **All areas 10/10** | |

Phases 1–6 are the path to 10/10. Phase 7 is a stretch that turns the project
into something you could actually run for real users.

**Why this order.** CI must come first — without it none of the other claims
are verifiable. Security comes before tests because security regressions are
the most catastrophic class of bug. Tests come before efficiency because
"make it fast" without tests means "make it fast and wrong." Accessibility
and code quality are independent and can be parallelised.

---

## Phase 1 — CI + quality gates (1–2 days)

Without this, every other improvement is a lie a reviewer can't verify.

### Backend

- Add **`.github/workflows/ci.yml`** running:
  - `pip install -r requirements.txt -r requirements-dev.txt`
  - `ruff check . --output-format=github`
  - `mypy app --strict`
  - `pytest --cov=app --cov-report=xml --cov-fail-under=85`
  - Upload coverage to **Codecov** with PR diff comments.
- Create **`backend/requirements-dev.txt`**: `ruff`, `mypy`, `pytest-cov`,
  `pytest-asyncio` (already implicit), `types-passlib`.
- Add **`backend/pyproject.toml`** sections:
  ```toml
  [tool.ruff]
  target-version = "py311"
  line-length = 100
  [tool.ruff.lint]
  select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM", "RUF", "ASYNC"]
  [tool.mypy]
  strict = true
  plugins = ["pydantic.mypy"]
  ```

### Frontend

- Workflow steps:
  - `npm ci`
  - `npm run typecheck`
  - `npm run lint`
  - `npm test -- --coverage` (added in Phase 3)
  - `npm run build`  (catches SSR-only errors `typecheck` can't)
- Add **Prettier** + `.prettierrc` + `prettier --check src/`.
- Add **`@next/bundle-analyzer`** with a `npm run analyze` script.

### Repo-level

- **Branch protection** on `main`: require CI green + 1 approval + linear history.
- **`Dependabot`** weekly for `pip`, `npm`, GitHub Actions.
- **`pre-commit`** config running ruff + prettier (optional but recommended).

### Acceptance

- A PR with a deliberate lint violation **cannot merge**.
- A PR that breaks a backend test **cannot merge**.
- Codecov shows coverage delta on every PR.

---

## Phase 2 — Security hardening (3–5 days)

Order strictly by blast radius.

### 2.1 Move JWT to `HttpOnly` cookies + CSRF (Day 1)

| Before | After |
|---|---|
| Access token in `localStorage` → XSS-exfiltratable | Access token in `__Host-access` `HttpOnly`, `SameSite=Lax`, `Secure` cookie + refresh token in `__Host-refresh` `HttpOnly`, `SameSite=Strict`, longer TTL |

- Backend (`app/api/v1/auth.py`):
  - `/login`, `/register`, `/refresh` set cookies via `Response.set_cookie(...)`.
  - `oauth2_scheme` (used by `require_user`) replaced by a small dependency
    that reads `request.cookies["__Host-access"]` first, falls back to the
    `Authorization` header for machine clients.
  - `/logout` clears both cookies.
- Frontend (`src/lib/client-api.ts`):
  - Add `credentials: "include"` to every `fetch`.
  - **Drop** `useAuthStore.token`; replace with a minimal `useAuthStore.user`
    that's hydrated from `/auth/me` after page load (cookie is the source of
    truth, not state).
- **CSRF**: state-changing endpoints (`POST`/`PUT`/`DELETE`) require an
  `X-CSRF-Token` header that's checked against a double-submit cookie
  (`__Host-csrf`).
- Update `auth-store.ts` and any place reading `state.token` (≈ 6 files).

### 2.2 Rate limiting on auth (Day 1)

- Add `slowapi` → backend `requirements.txt`.
- `/auth/login`: **5 req/min/IP**, **20 req/hour/email**.
- `/auth/register`: **3 req/hour/IP** (sign-up abuse).
- `/onboarding/progress` autosave: **120 req/min/user**.
- Returns 429 with `Retry-After`.

### 2.3 Hard-fail on default secrets in production (½ day)

- `core/config.py`: if `is_production` and `secret_key` is the default → raise
  on startup. Same for `database_url`, `demo_password`, etc.
- Health check `/readyz` returns 503 until critical env vars are validated.

### 2.4 Security headers + HSTS (½ day)

- Add **Starlette middleware** in `app/main.py` setting:
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: geolocation=(), camera=(), microphone=()`
  - `Content-Security-Policy:` strict with nonces (Next.js supports it).
- Frontend `next.config.mjs`: matching `headers()` so the SPA serves identical
  policies.
- Target: A grade on https://securityheaders.com.

### 2.5 Password policy + breach check (½ day)

- `schemas/auth.py` `RegisterRequest`:
  - `password: str = Field(min_length=12, max_length=128)`.
  - Validator rejecting passwords in **HIBP top-100k breached list** (vendored
    bloom filter, ~600 KB).
- Optional: zxcvbn score ≥ 3 (Python `zxcvbn-py`).

### 2.6 Audit log writer (½ day)

- New `app/services/audit.py` with `record(actor_user_id, action, resource_*, request)`.
- Decorator `@audited("auth.login")` on auth, connection, privacy endpoints
  → writes to the existing `audit_log` table (partitioned, ready to receive).
- Tested with a `test_audit_log_writes_on_login`.

### 2.7 GDPR/DPDP data-rights implementation (1 day)

- `POST /privacy/export`:
  - Creates a `DsrJob(kind=export, status=queued)`.
  - Background task (`BackgroundTasks` for MVP, Celery for prod) assembles
    user data → JSON bundle → S3 signed URL → email link.
- `POST /privacy/erase`:
  - Creates `DsrJob(kind=erase)` with `48h` grace.
  - Scheduler (APScheduler in MVP) sweeps overdue jobs → cascade delete
    user + all child rows (FK cascades) + purges raw_* partitions.
- Both endpoints write an `audit_log` entry.
- Tested with `test_export_creates_job`, `test_erase_after_grace`.

### 2.8 Envelope encryption for stored provider tokens (½ day)

- `core/crypto.py`: `Fernet` wrapper that takes the symmetric key from
  `ENCRYPTION_KEY` env var (in prod: KMS-resolved).
- `models/connection.py`: a `@hybrid_property` that wraps `access_token_enc`
  with encrypt-on-set / decrypt-on-get.
- Migration to re-encrypt existing rows.

### 2.9 Dependency vulnerability scanning (½ day)

- CI step: `pip-audit` for Python, `npm audit --audit-level=high` for Node.
- Dependabot already opens PRs from Phase 1.

### Acceptance

- **OWASP Top-10 self-review** with a one-page report committed to
  `docs/SECURITY-REVIEW.md` covering each category.
- **`securityheaders.com` → A grade** on the deployed app (or `curl -I` on a
  staging server demonstrating headers).
- **No `localStorage.getItem("…token")`** anywhere in the frontend
  (grep-verified).
- **`pip-audit` → 0 HIGH/CRITICAL**.

---

## Phase 3 — Test coverage (4–6 days)

Biggest single gap. 10/10 testing = backend ≥ 90%, frontend ≥ 80%,
E2E covering the critical paths, mutation testing on the math.

### 3.1 Frontend unit + component tests (2 days)

- Add **vitest** + `@testing-library/react` + `jsdom` + `@vitest/coverage-v8`.
- **Tests to write** (highest-value first):
  | File under test | Test file | What it locks down |
  |---|---|---|
  | `lib/questionnaire.ts` | `questionnaire.test.ts` | `isVisible` matches backend, null vs undefined gotcha |
  | `lib/format.ts` | `format.test.ts` | tCO2e formatting boundaries |
  | `lib/use-auth-guard.ts` | `use-auth-guard.test.tsx` | redirects only after hydration |
  | `store/auth-store.ts` | `auth-store.test.ts` | persist hydration, 401 → logout |
  | `components/onboarding/Questionnaire.tsx` | `Questionnaire.test.tsx` | visibleIf branching, R0 precision math, resume initialStep, "Not sure" skip |
  | `components/onboarding/AuthGate.tsx` | `AuthGate.test.tsx` | password mismatch, mode toggle resets confirm |
  | `components/ui/ConfirmDialog.tsx` | `ConfirmDialog.test.tsx` | Escape closes, focus moves to confirm |
  | `components/ui/MethodBadge.tsx` | `MethodBadge.test.tsx` | imputed → "Inferred", method variants |
  | `components/dashboard/BenchmarkGauge.tsx` | `BenchmarkGauge.test.tsx` | privacyAdjusted note renders, below/above tone |
- **Coverage targets** in `vitest.config.ts`:
  ```ts
  coverage: { thresholds: { lines: 80, functions: 80, branches: 75 } }
  ```

### 3.2 Backend DB-mode tests (1 day)

The current tests run in seed mode. The actual SQL paths in
`dashboard.py` / `bank_sync.py` / `attribution.py` are unverified.

- Add **`testcontainers-python[postgres]`** to `requirements-dev.txt`.
- New `tests/test_db_integration.py` with a session-scoped Postgres
  container + Alembic `upgrade head` fixture.
- **Tests:**
  - `test_recompute_upgrades_estimated_to_spend` — onboard → ingest 50 txns →
    assert all 4 categories `method=spend`, `confidence=0.80`.
  - `test_bank_only_imputes_energy` — onboard → ingest bank only →
    assert energy is `imputed=true`, `confidence=0.55`.
  - `test_meter_promotes_to_activity` — above + meter →
    assert energy `method=activity`, `confidence=0.95`.
  - `test_attribution_decomposes_to_total` — seed reads with known kWh and
    grid intensity → assert `behavioral + structural ≈ total` to 1 dp.
  - `test_recompute_idempotent` — run twice, assert no row growth.
- These can run in CI with `services: postgres:16` on the GitHub runner.

### 3.3 End-to-end tests with Playwright (1 day)

- `npm i -D @playwright/test`.
- `frontend/e2e/`:
  | Spec | Flow |
  |---|---|
  | `onboarding-new-user.spec.ts` | register → answer 8 → estimate → reveal → biome visible |
  | `returning-user.spec.ts` | login as demo → lands on `/dashboard` (no questionnaire flash) |
  | `connect-bank.spec.ts` | login → click Connect bank → footprint updates → category method=Spend-based |
  | `logout.spec.ts` | open account menu → log out → confirm modal → land on `/` |
  | `resume.spec.ts` | start onboarding → reload mid-flow → resume at saved step with saved answers |
  | `a11y.spec.ts` | run `@axe-core/playwright` against `/`, `/onboarding`, `/dashboard`, `/insights` → 0 violations |

- CI job runs the suite against a fresh backend container.

### 3.4 Mutation testing on the math (½ day)

- Add **`mutmut`** to `requirements-dev.txt`.
- Run on the pure-math modules: `services/carbon.py`, `services/impute.py`,
  `services/benchmark_stats.py`, `services/attribution.py`,
  `services/estimator.py`.
- Target: **kill rate ≥ 80%** on each module. Surviving mutants → either add
  the test that catches them or document why they're equivalent.

### 3.5 Property-based test for the estimator (½ day)

- **`hypothesis`** → generate random valid answer dicts.
- Assert invariants:
  - All categories non-negative.
  - Sum of categories == `total_tco2e` (within rounding).
  - `health ∈ [0,1]`, monotone-decreasing in total.
  - `no_car ⇒ transport ≤ has_car` strictly.

### Acceptance

- Coverage badges in README:
  - Backend ≥ **90%** (line + branch).
  - Frontend lib/stores/hooks ≥ **80%**, components ≥ **70%**.
- Mutation kill rate ≥ **80%** on math modules.
- Playwright suite green in CI.
- New `tests/README.md` documenting what each layer tests and why.

---

## Phase 4 — Efficiency polish (2–3 days)

### 4.1 HTTP caching headers (½ day)

Per `docs/API-DESIGN.md §9` (which is correct, just not implemented):

- `GET /footprint/summary` → `Cache-Control: private, max-age=60`
- `GET /community/benchmark` → `Cache-Control: private, max-age=300`
- `GET /onboarding/questions` → `Cache-Control: public, max-age=3600, immutable`
- ETag generation for any endpoint with stable identity.

### 4.2 Request-level data caching with TanStack Query (1 day)

- `npm i @tanstack/react-query`.
- Wrap the app in a `QueryClientProvider`.
- Convert page-mount `useEffect(fetch)` patterns to `useQuery`:
  - `DashboardClient` (footprint + recommendations + benchmark in parallel).
  - `InsightsClient`, `ActClient`, `ProfileClient`.
- Default `staleTime: 30s`, `gcTime: 5min`, `refetchOnWindowFocus: true`.
- Optimistic updates for `Act` button on recommendations.
- **Removes**: ~150 lines of effect-based fetch boilerplate.

### 4.3 Connection-pool tuning + observability (½ day)

- `db/session.py`:
  ```python
  create_async_engine(
      settings.database_url,
      pool_pre_ping=True,
      pool_size=10, max_overflow=20,
      pool_recycle=1800,
      echo=settings.echo_sql,
  )
  ```
- Add `prometheus-fastapi-instrumentator` → expose `/metrics`.
- Grafana panel for p50/p95/p99 per endpoint (template committed).

### 4.4 Bundle audit + tree-shaking pass (½ day)

- `@next/bundle-analyzer` from Phase 1: review the report.
- Move heavy three.js imports behind dynamic boundaries (already done for
  `BiomeScene`; verify nothing on landing imports it eagerly).
- Audit `lucide-react` — already on `optimizePackageImports`.
- Switch any default `import * as THREE` to named imports where possible.
- Target: landing First Load JS **< 120 kB**, dashboard < 200 kB.

### 4.5 Brotli compression + image budget (½ day)

- FastAPI: `GZipMiddleware(minimum_size=1000)`. (Brotli at the CDN edge in prod.)
- Lighthouse CI in the Playwright job:
  - Performance ≥ 95
  - LCP < 2.0s on the dashboard

### Acceptance

- `next build` shows landing < 120 kB and dashboard < 200 kB First Load JS.
- `pytest-benchmark` or k6 load test: `/footprint/summary` p95 < 50 ms with
  cached snapshot.
- Lighthouse CI in PRs: **Performance ≥ 95** on landing and dashboard.

---

## Phase 5 — WCAG 2.1 AA + screen-reader pass (2–3 days)

### 5.1 Quick wins (½ day)

- **Skip-to-content** link in `AppShell` (visible on focus only).
- **Focus management on route change**: `useEffect(() => h1Ref.current?.focus(), [pathname])` in `AppPage`.
- **`aria-invalid` + `aria-describedby`** on `AuthGate` password fields when
  mismatch shown.
- **Required-field indicators**: visually + `aria-required="true"`.
- **Error summary at top of form** linking to the offending field.

### 5.2 Keyboard alternative for the 3D biome (1 day)

The biggest a11y gap. Today, tap-to-plant and drag-to-orbit are pointer-only.

- Add a sibling **"Plant a tree" button** under the canvas, focusable, with the
  same `plantTree` call (random spherical direction).
- Custom `<KeyboardOrbitControls>`: ArrowLeft/Right rotate azimuth, ArrowUp/Down
  rotate polar, +/− zoom. Honour `prefers-reduced-motion`.
- Canvas is focusable (`tabIndex={0}`) with an instruction tooltip on focus
  ("Use arrow keys to orbit, Space to plant").

### 5.3 Axe-core in CI (½ day)

- Phase 3.3's `a11y.spec.ts` runs `@axe-core/playwright` against every public
  route. **Zero violations** is the gate.

### 5.4 Manual screen-reader walk-through (½ day)

- Document a 10-minute walkthrough in `docs/A11Y-REPORT.md`:
  - NVDA on Windows / VoiceOver on macOS
  - Cover: landing → onboarding (one question) → estimate reveal → dashboard
    → confirm-logout
- Capture any issues; fix or document why deferred.

### 5.5 Contrast audit (½ day)

- Run `axe-core` and **manual Stark / Polypane** check on:
  - Category accent colors on `bg-base` and `surface-1`
  - `text-text-lo` on every surface
  - Warning/danger tones
- Adjust tokens in `globals.css` if any fail AA (≥ 4.5:1 for body, ≥ 3:1 for
  large text and non-text components).

### Acceptance

- `@axe-core/playwright` runs in CI: **0 violations** on every public route.
- Lighthouse a11y: **100** on every route.
- `docs/A11Y-REPORT.md` documents NVDA + VoiceOver walkthroughs.
- 3D biome usable by keyboard alone (verifiable in CI: Playwright with
  `await page.keyboard.press("ArrowLeft")` etc.).

---

## Phase 6 — Code-quality polish (1–2 days)

These are mostly **refactors** that an external code review would flag.

### 6.1 Module splits (½ day)

| Before | After |
|---|---|
| `services/estimator.py` (questionnaire + estimator + R0 voi, ~300 lines) | `services/questionnaire.py` (QUESTIONS + helpers), `services/estimator.py` (math only), `services/voi.py` (`_apply_voi` + `_voi_order`) |
| `services/bank_sync.py.recompute_footprint` (~80 lines) | extract `_collect_spend`, `_collect_energy`, `_merge_categories` private helpers |
| `lib/types.ts` (everything) | `lib/types/{auth,footprint,onboarding,connection,benchmark}.ts` re-exported via barrel |

### 6.2 De-duplication (½ day)

- Single `useLogoutWithConfirm()` hook used by both `AccountMenu` and
  `ProfileClient` (currently identical `confirmLogout` bodies).
- Single `useApiQuery` wrapper around TanStack Query that injects auth state.

### 6.3 ADRs (½ day)

`docs/adr/` with short Architecture Decision Records (template: Status, Context,
Decision, Consequences). Initial set:

- **ADR-0001** — Why the questionnaire is server-defined (single source of truth).
- **ADR-0002** — Why we accept R0/R1/R2/R4 as heuristics with a "seam" for ML.
- **ADR-0003** — Why JWT in cookies (after Phase 2.1) instead of localStorage.
- **ADR-0004** — Why partition `raw_*` tables (retention + scan bounds).
- **ADR-0005** — Why the bank-only-no-utility design in the sandbox provider
  (forces R1 to fire).

### 6.4 API docs polish (½ day)

- Every endpoint gets `summary=` + `description=` + a Pydantic `Config.json_schema_extra` example.
- Custom OpenAPI title, contact, license.
- Swagger UI exposes the `Try it out` flow.

### Acceptance

- `ruff check` / `mypy --strict` / `eslint` → **0** issues.
- **No file > 250 lines** (soft target; doc files exempt).
- **Cyclomatic complexity < 10** per function (`ruff` rule `C901`).
- `docs/adr/` has ≥ 5 ADRs.

---

## Phase 7 — Production readiness (bonus, 3–5 days)

Not required for 10/10 on the five focus areas, but turns this into something
you could deploy for real users.

- **Multi-stage Dockerfiles** for backend and frontend; non-root user; distroless final.
- **`docker-compose.yml`** with Postgres for local dev; one-command up.
- **Health checks** that actually ping the DB (the current `/healthz` returns OK regardless).
- **OpenTelemetry tracing** (FastAPI + Next.js Edge runtime).
- **Structured JSON logging** with correlation IDs (`X-Request-Id` middleware exists; wire it through).
- **Sentry** (or alternative) for error reporting on both ends.
- **CSP nonces** generated per-request in Next.js middleware.
- **Database backups** — schedule + retention + restore-test runbook.
- **Runbook** for the top 5 incidents (DB failover, runaway recompute, leaked secret, expired refresh tokens, mass DSR job).
- **`docs/PRODUCTION-CHECKLIST.md`** — the SRE sign-off list.

---

## Acceptance evidence (committed to the repo)

When all six core phases are done:

```
.github/workflows/ci.yml         green on every PR; required for merge
docs/SECURITY-REVIEW.md          OWASP Top-10 self-review with file refs
docs/A11Y-REPORT.md              NVDA + VoiceOver walkthrough, axe-core results
docs/PERFORMANCE-REPORT.md       Lighthouse scores + bundle sizes
docs/adr/0001..N.md              architecture decisions
tests/README.md                  what each test layer covers and why
README.md badges                 CI, coverage, security, license
```

---

## Effort summary

| Phase | Days | Cumulative | Score after phase |
|---|---|---|---|
| **1 — CI + gates** | 1–2 | 1–2 | foundation (no score lift on its own) |
| **2 — Security** | 3–5 | 4–7 | Security 6 → 10 |
| **3 — Testing** | 4–6 | 8–13 | Testing 6 → 10 |
| **4 — Efficiency** | 2–3 | 10–16 | Efficiency 8 → 10 |
| **5 — Accessibility** | 2–3 | 12–19 | Accessibility 8 → 10 |
| **6 — Code quality** | 1–2 | 13–21 | Code Quality 8 → 10 |
| **7 — Production (bonus)** | 3–5 | 16–26 | deploy-ready |

**Total to 10/10 on the five focus areas: 13–21 days of focused work**
(one engineer; double if you context-switch).

---

## Honest caveats

- **"10/10 testing" is partly a moving target.** Even with 90% coverage +
  mutation testing + E2E + property-based, a senior reviewer can always
  point to something missing (chaos tests? contract tests with consumer
  apps? performance regression tests?). The plan above gets to "no
  reasonable reviewer would withhold a 10."
- **Real security audit** by a human (not just OWASP self-review) costs $$$.
  Phase 2 gets to "passes a competent self-review + automated scanners";
  a 10/10 for a regulated production system would add a third-party pen test.
- **WCAG 2.1 AA is binary** (you conform or you don't), but **AAA is much
  harder**. The plan targets AA conformance; AAA is out of scope.
- **The R0/R1/R2/R4 heuristics remain heuristics.** Replacing them with
  learned models is a separate, much larger research effort —
  out of scope for this plan, which is about engineering quality.

---

*This plan is a living document. As items land, tick them off
(`- [x]`) and link the PR.*
