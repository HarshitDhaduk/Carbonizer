# Carbonizer

**Automated, honest, personal carbon tracking — with no manual logging.**

The first carbon tracker that gets *more accurate the longer you use it*, instead of less. Sign up in 60 seconds, never enter another kWh by hand, and watch your *Living Planet* react in real time to the decisions you actually make.

| | |
|---|---|
| 🌍 **Try it live** | [**carbonizer-lyart.vercel.app**](https://carbonizer-lyart.vercel.app/) |
| 📡 **Live API** | [carbonizer-api.onrender.com/docs](https://carbonizer-api.onrender.com/docs) |
| 🎯 **Problem-statement audit trail** | [`docs/PROBLEM-STATEMENT.md`](docs/PROBLEM-STATEMENT.md) |
| 📚 **Architecture deep-dive** | [`docs/DESIGN.md`](docs/DESIGN.md) |
| 🚀 **Deploy your own** | [`docs/DEPLOY.md`](docs/DEPLOY.md) |
| 🤝 **Contributing** | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| 📝 **Changelog** | [`CHANGELOG.md`](CHANGELOG.md) |

---

## 1 · The problem (and why prior attempts have failed)

Households are responsible for **~70%** of consumption-driven greenhouse-gas emissions, yet **personal climate tools have failed to make a dent.** The pattern is consistent across every existing app:

> A user installs it on Sunday, logs a few meals on Monday, by Friday they've stopped, and by month-end they uninstall. The carbon footprint never gets accurate because the data was never automatic.

We mapped the root failure modes:

| Failure mode | What users feel | What it really is |
|---|---|---|
| **Manual logging tax** | "I have to type every receipt?" | The product asks the user to do the work that the platform should do. |
| **Connect-three-things wall** | "I only have a bank account — give me a number anyway." | Coverage is brittle when any one data source is missing. |
| **Spend-blind accounting** | "Why does buying expensive sustainable shoes increase my score?" | £-to-CO₂e mapping penalises paying more for greener choices. |
| **Cleaner-grid plagiarism** | "I cut my electricity 15% but the app gives me 100% credit." | A drop on the dashboard isn't the same as a behaviour change. |
| **Privacy theatre** | "Am I being compared with a cherry-picked benchmark? Is my data leaking?" | Aggregated comparisons leak both direction (selection bias) and individuals (no DP). |

**Carbonizer is the design that closes each of these in turn.** None individually is novel — the contribution is treating them as a connected system and shipping them together.

---

## 2 · Who it's for

The target user is a **climate-curious adult with a UK bank account who has tried a footprint app before and lost interest.** They:

- Want **the truth about their footprint**, not a vanity number.
- Will **connect one or two data sources** if it's two clicks each.
- Will **never** log meals, weigh groceries, or type kWh values.
- Care about **privacy** — they trust the app with bank metadata only if it stays on the platform.
- Respond to **agency, not guilt** — "here's the one change that cuts the most" beats "you're above average."

This guides every product decision below.

---

## 3 · How Carbonizer solves it — feature ↔ problem map

Each R-track is a directly-addressable answer to one of the failure modes above. They compose into a single experience.

| Problem | Solution | Implementation |
|---|---|---|
| Manual logging tax | **Connect-once ingestion** + sandbox/real provider abstraction behind a `Protocol` so adapters drop in without changing the pipeline | [`backend/app/services/providers.py`](backend/app/services/providers.py) |
| Connect-three-things wall | **R1 — Bank-as-hub imputation.** Bank-only users get a real footprint for energy + food + transport with explicit `confidence` and an "Inferred" badge | [`backend/app/services/impute.py`](backend/app/services/impute.py) |
| Spend-blind accounting | **R2 — Price-elasticity decoupling + merchant priors.** Carbon factor varies per merchant within an MCC; the £→CO₂e mapping respects price elasticity per category | [`backend/app/services/carbon.py`](backend/app/services/carbon.py) |
| Cleaner-grid plagiarism | **R3 — Behavioural vs structural attribution.** ΔCO₂e is decomposed into "your usage" and "grid change"; the user is only credited for the behavioural share | [`backend/app/services/attribution.py`](backend/app/services/attribution.py) |
| Privacy theatre | **R4 — IPW + Laplace DP + k-anonymity.** Selection-bias-corrected mean, (ε)-DP release, cohort suppression below k=50 | [`backend/app/services/benchmark_stats.py`](backend/app/services/benchmark_stats.py) |
| Onboarding-fatigue tax | **R0 — Value-of-Information question ordering.** Highest-variance question first; a precision meter climbs *faster than step progress* so users see accuracy as the reward | [`backend/app/services/voi.py`](backend/app/services/voi.py) |
| "I have no idea how accurate this is" | **Progressive Data Depth.** Every category carries a method badge (estimated → inferred → spend → activity) + a 0–1 confidence number — accuracy becomes a visible engagement loop | [`backend/app/services/bank_sync.py:_merge_categories`](backend/app/services/bank_sync.py) |

---

## 4 · The user experience — what a real visitor sees

1. **Landing** — the **3D Living Planet** at the centre is health-mapped to the user's footprint *before* sign-up. Three modes: drag to orbit, tap to plant, [Plant a tree] button + Space/Enter for keyboard.
2. **Sign in / register** in ~10 seconds — cookies handle the session, no password manager dance.
3. **Onboarding** — **8 questions ordered by value-of-information**, dependency-aware. Pick "No car" and the next 1–2 questions get skipped. A live **precision meter** shows accuracy climbing as you answer — the reward is *certainty about your own number*.
4. **Day-0 reveal** — your annual tonnes, your biome state, and the top-three categories. Every figure carries a method badge — there's nothing implicit.
5. **Connect a source** (sandbox today) → the corresponding category's badge flips from *Estimated* to *Spend-based* or *Activity-based*. The planet's health re-renders in real time.
6. **Insights** — bar chart sorted by impact, the R3 "behaviour vs grid" attribution panel, and the data-quality counter ("3 of 4 categories measured").
7. **Act** — top three high-impact nudges, ranked by `(carbon saved × money saved)`. One-tap actions where they exist.
8. **Community** — benchmark vs households like yours, k-anonymised at k=50, DP-noised on read.
9. **Profile** — the user's own data, a one-click GDPR/DPDP export, and the 48-hour-grace erase flow.

**Try it now**: [carbonizer-lyart.vercel.app](https://carbonizer-lyart.vercel.app/) → register with any email + a 12-character password.

---

## 5 · What we shipped — concrete artifacts

| Artifact | Count / state |
|---|---|
| Backend tests | **76 unit + 8 DB-mode integration (testcontainers Postgres 16)** |
| Frontend unit tests | **33 vitest specs** with coverage thresholds enforced in CI |
| End-to-end tests | **14 Playwright specs** covering auth flow, a11y (axe-core), questionnaire, keyboard nav, connect-source |
| Property-based tests | **13 Hypothesis properties** (estimator + carbon/impute services) |
| Mutation tests | **mutmut** weekly on the pure-math services |
| Security | **OWASP Top 10 self-review** ✓ — see [`docs/SECURITY-REVIEW.md`](docs/SECURITY-REVIEW.md). HttpOnly cookies + CSRF, Argon2id, rate limits, hard-fail on default secrets, envelope encryption for provider tokens. |
| Accessibility | **WCAG 2.2 AA verified** — see [`docs/A11Y-REPORT.md`](docs/A11Y-REPORT.md). NVDA + VoiceOver + TalkBack walkthroughs documented for all 4 critical flows. |
| Architecture decisions | **5 ADRs** in [`docs/adr/`](docs/adr/) |
| CI gates | ruff + mypy --strict + ruff `C901` + pytest (≥ 70%) + vitest (coverage thresholds) + Playwright + Lighthouse + pip-audit + npm audit |
| Live deploy | Frontend on **Vercel**, API on **Render** (Dockerised, multi-stage, non-root), Postgres on **Neon** |
| Production-ready docs | [`docs/DEPLOY.md`](docs/DEPLOY.md), [`docs/RUNBOOK.md`](docs/RUNBOOK.md), [`docs/PRODUCTION-CHECKLIST.md`](docs/PRODUCTION-CHECKLIST.md) |

---

## 6 · Architecture at a glance

```
┌────────────────────────────────────────────────────────────────┐
│                  Next.js 16 (App Router) + Three.js            │
│                                                                │
│  Landing → AuthGate → Onboarding (R0 VoI) → Day-0 reveal →     │
│  Dashboard / Insights (R1 imputed, R3 attribution) /           │
│  Act / Community (R4 private benchmark) / Profile              │
└──────────────────┬─────────────────────────────────────────────┘
                   │  Same-origin JSON over HTTPS
                   │  HttpOnly cookies + CSRF double-submit
┌──────────────────▼─────────────────────────────────────────────┐
│              FastAPI · Pydantic v2 · SQLAlchemy 2.0            │
│                                                                │
│  auth · onboarding · connections · footprint · attribution     │
│  recommendations · community · privacy · health                │
│                                                                │
│  services:                                                     │
│   questionnaire (R0 data + helpers)                            │
│   voi           (R0 scoring + ordering)                        │
│   estimator     (Day-0 math)                                   │
│   providers     (sandbox bank + meter behind a Protocol)       │
│   carbon        (MCC routing · merchant priors · elasticity)   │
│   bank_sync     (idempotent upsert + recompute)                │
│   impute        (R1 bank-as-hub + confidence)                  │
│   attribution   (R3 grid vs usage decomposition)               │
│   benchmark_stats (R4 IPW + Laplace DP)                        │
│   dsr / dsr_export (GDPR Art. 15 / 17 + DPDP §11 / §12)        │
│   audit         (best-effort append-only log)                  │
└──────────────────┬─────────────────────────────────────────────┘
                   │
       ┌───────────▼───────────────────┐
       │  PostgreSQL 16 (Neon)         │
       │   Partitioned raw_*, ledger,  │
       │   snapshots, cohorts, audit   │
       │   Alembic · Argon2id · Fernet │
       └───────────────────────────────┘
```

---

## 7 · Scope decisions (and where to plug in the real thing)

We were deliberate about what's **real engineering** vs. **MVP standing in for production data sources**. Each "stand-in" has a clean seam where the production version drops in.

| MVP stand-in | Production version | Seam |
|---|---|---|
| `SandboxBankProvider` produces deterministic synthetic transactions | GoCardless / TrueLayer / Plaid adapter | `services.providers.BankProvider` Protocol |
| `SandboxMeterProvider` produces synthetic half-hourly reads | Octopus Energy OAuth / DCC / n3rgy | `services.providers.MeterProvider` Protocol |
| Hand-curated 15-merchant prior table (R2) | Learned per-merchant intensities + name-embedding model | `_MERCHANT_MULTIPLIER` in `services.carbon` |
| Per-category price elasticities picked from economics | Estimated from population data | `_CATEGORY_PRICE_ELASTICITY` in `services.carbon` |
| R1 blend weights `prior × (0.6 + 0.4 × signal)` hand-set | Learn `P(energy, transport \| spend, demographics)` on the multi-source anchor set | `impute.impute_from_bank()` call signature unchanged |
| R0 spread-based VoI | Expected information gain on the R1 posterior, re-ranked adaptively | `services.voi._question_spread()` |
| R4 IPW uses a constant +10% selection skew | Per-cohort propensity scores via logistic regression on connector vs population features | `benchmark_stats.ipw_population_mean()` |
| `ENCRYPTION_KEY` rotation via env-var swap | KMS-backed envelope with automatic re-encryption on read | `core.crypto` Fernet wrapper |
| GDPR `/privacy/erase` sweep called manually in dev | Render Cron Job (production) or any external cron | `dsr.sweep_overdue_erasures()` |
| GoCardless / TrueLayer not wired (live OAuth registration is paid) | Real adapter | Protocol-compatible class |
| Mobile telematics not built (background GPS needs native code) | Rust + UniFFI core | Documented in `docs/DESIGN.md §9` |
| NLP transaction classifier not yet trained | Fine-tuned RoBERTa (~87% F1 cited in docs) | `services.carbon.categorize()` falls back to MCC routing today |

The point isn't to wave away the gaps — it's to show that **the production path doesn't change the architecture**.

---

## 8 · Running locally

Full setup in [`CONTRIBUTING.md`](CONTRIBUTING.md). Short version:

```bash
# Backend (seed mode, no Postgres needed)
cd backend
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload                       # http://127.0.0.1:8000

# Frontend (in another terminal)
cd frontend
npm install --no-audit --no-fund --legacy-peer-deps
npm run dev                                         # http://localhost:3000
```

Want the **DB-mode** path? Flip `USE_DB=true` in `backend/.env`, set `DATABASE_URL` to a Postgres URL (Neon free tier works), run `alembic upgrade head`. The dev rewrite makes the frontend call the local backend at `/api/v1` — same-origin like in production.

---

## 9 · Where this goes next

The MVP closes the loop for an individual user. The product roadmap (in [`docs/DESIGN.md §9`](docs/DESIGN.md)) is the journey from "your number" to "your collective effect":

- **Real Open Banking** (GoCardless / TrueLayer) — moves coverage from sandbox-deterministic to user-data-driven.
- **Smart-meter OAuth** (Octopus / DCC) — flips energy from spend/imputed to activity for everyone.
- **Mobile telematics** (Rust + UniFFI) — flips transport from spend to activity for everyone.
- **Personal Carbon Trading marketplace** — a stretch goal where verified reductions become tradeable.
- **Employer / municipality dashboards** — Carbonizer for a company / town, with cohort-level differential privacy.

---

## Repository map

```
docs/                 design specs + deploy + runbook + ADRs
  DESIGN.md           product & architecture deep-dive
  UI-UX-DESIGN.md     visual language + screens
  DB-SCHEMA.md        database design + partitioning strategy
  API-DESIGN.md       REST contract + auth model
  DATA-STRATEGY.md    real-data + R0–R4 detailed rationale
  SECURITY-REVIEW.md  OWASP top-10 self-review
  A11Y-REPORT.md      WCAG 2.2 AA walkthroughs
  DEPLOY.md           Neon + Render + Vercel deploy guide
  RUNBOOK.md          top-5 incident playbook
  PRODUCTION-CHECKLIST.md  pre-launch SRE sign-off
  adr/                load-bearing architecture decisions

backend/              FastAPI service (Dockerised, multi-stage)
  app/                core / db / models / schemas / services / api
  alembic/            migrations
  tests/              pytest + Hypothesis + testcontainers
  Dockerfile          multi-stage Python 3.11-slim, non-root, HEALTHCHECK
  render.yaml         deploy spec (root-level)

frontend/             Next.js 16 + React 19 + React Three Fiber
  src/app/            routes (App Router)
  src/components/     biome / landing / onboarding / dashboard / insights / act / profile / providers
  src/lib/            api clients, types, queries, hooks, design tokens
  src/store/          Zustand stores
  e2e/                Playwright specs (auth, a11y, questionnaire, keyboard-nav, connect-source)
  vercel.json         Vercel rewrites + build config

.github/workflows/
  ci.yml              backend + frontend + e2e + Lighthouse on every PR
  mutmut.yml          weekly mutation testing
  dep-audit.yml       weekly all-severity dep scan

CHANGELOG.md          Keep-a-Changelog
CONTRIBUTING.md       new-contributor green-CI-in-30-minutes guide
```
