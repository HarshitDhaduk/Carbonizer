# Carbonizer

A personal carbon-tracking web app that turns everyday spending, travel and energy
use into a **Living Planet** — and tells you the few changes that shrink both your
footprint and your bills.

Live UI (Next.js + Three.js) backed by a FastAPI service over PostgreSQL.
Demo account: **`demo@carbonizer.app` / `demo12345`**.

---

## 1. Chosen vertical

**Climate & sustainability — consumer carbon tracking.**

The vertical sits at the intersection of:

- **Consumer climate action** — household consumption accounts for a large share of
  global GHG emissions, yet most regulation targets corporates and governments.
- **Open Banking + IoT** — PSD2 transaction APIs and smart-meter feeds make it
  possible to track real activity without asking the user to log anything by hand.
- **Behavioral economics** — sustainable choices fail when accuracy demands effort
  users won't give; defaults, social benchmarks and tangible feedback close that gap.
- **ML for carbon accounting** — turning transactions and meter reads into
  calibrated CO₂e requires classification, imputation, and causal attribution.

The target user is an individual who wants to **understand and shrink their
footprint with near-zero effort** — never type a kWh, never keep a food diary.

See [`docs/DESIGN.md`](docs/DESIGN.md) for the full product brief and
[`docs/DATA-STRATEGY.md`](docs/DATA-STRATEGY.md) for the data acquisition strategy.

---

## 2. Approach and logic

### The core reframe

Most personal-carbon apps fail because they treat the footprint as **a number that
needs more user input to refine**. Carbonizer treats it as a **calibrated posterior
distribution**:

- Each data source is a **noisy observation** that shrinks variance.
- Each unmeasured category is a **wide prior** carrying explicit uncertainty.
- Accuracy becomes a continuous gradient rather than a binary "have data / don't".

This single move unifies the design — confidence becomes a first-class field on
every category, the UI surfaces *how* a figure was derived, and bank-only users
get a usable footprint instead of "please connect three more things."

### Progressive Data Depth — the spine

Every user starts with a **Day-0 estimate** from an 8-question onboarding form,
then each connection visibly **upgrades** categories along the data-quality
ladder:

```
estimated  →  inferred  →  spend  →  activity
   0.30        0.55         0.80       0.95     ← confidence
```

The `method` badge isn't just a footnote — it's the engagement loop. *Improving
accuracy is the game.*

### Five research directions (the differentiating logic)

Each is documented in detail in
[`docs/DATA-STRATEGY.md` §9](docs/DATA-STRATEGY.md). They're implemented as MVPs
that produce believable behaviour today, with the seam where a learned model
plugs in clearly marked.

| ID | Idea | Tension it resolves |
|---|---|---|
| **R0** | **Value-of-Information onboarding.** Order questions by how much answering each one shrinks footprint uncertainty (footprint-spread × visibility), highest-yield first. Show an "estimate precision" meter that climbs **far faster than step progress**. | Accuracy ↔ friction. |
| **R1** | **Bank-as-hub imputation.** Most users only connect their bank. Treat it as a hub view: when a category has no direct transactions (e.g. energy), reconstruct it from the bank's spend signal and the onboarding prior, with explicit `confidence`, surfaced as **"Inferred"** until measured. | Coverage with one source. |
| **R2** | **Price ↔ carbon decoupling.** Pure spend-based accounting wrongly penalises paying more for a sustainable product. We apply merchant-level intensity multipliers (eco vs conventional within the same MCC) and a per-category **price-elasticity** of carbon: `co2e = factor · ref · (gbp/ref)^e` (e=1 for fuel/energy, e<1 for goods). | Spend-based blindness. |
| **R3** | **Honest reduction attribution.** A drop in energy emissions could be the user using less *or* the grid getting cleaner. We decompose ΔCO₂e exactly into **behavioral** (usage × old grid) and **structural** (new usage × grid change) terms, and credit the user only for the behavioral share. | Causal credit. |
| **R4** | **Privacy-preserving + selection-bias-corrected benchmarking.** Inverse-propensity weighting lifts the eco-skewed connector mean toward the true population, then a Laplace **(ε)-DP** release protects individuals. k-anonymity suppresses small cohorts. | Privacy + fairness. |

---

## 3. How the solution works

### Architecture

```
        ┌───────────────────────────────────────────────────────────┐
        │                  Next.js (App Router) + Three.js          │
        │                                                           │
        │  Landing  →  Onboarding (R0 VoI)  →  Day-0 reveal  →       │
        │  Dashboard / Insights (R1 imputed, R3 attribution) /       │
        │  Act / Community (R4 private benchmark) / Profile          │
        └────────────────────────┬──────────────────────────────────┘
                                 │  JSON over HTTPS  (JWT bearer)
        ┌────────────────────────▼──────────────────────────────────┐
        │             FastAPI · Pydantic v2 · SQLAlchemy 2.0         │
        │                                                            │
        │  auth · onboarding · connections · footprint · attribution │
        │  recommendations · community · privacy · health            │
        │                                                            │
        │  services:                                                 │
        │   estimator   (Day-0 + R0 VoI ordering)                    │
        │   providers   (sandbox bank + meter behind a Protocol)     │
        │   carbon      (MCC routing · merchant priors · elasticity) │
        │   bank_sync   (idempotent upsert + recompute)              │
        │   impute      (R1 bank-as-hub + confidence)                │
        │   attribution (R3 grid vs usage decomposition)             │
        │   benchmark_stats (R4 IPW + Laplace DP)                    │
        │   dashboard   (per-user reads, k-anon)                     │
        └────────────────────────┬──────────────────────────────────┘
                                 │
              ┌──────────────────▼─────────────────────┐
              │  PostgreSQL (partitioned raw_*, ledger,│
              │   snapshots, cohorts, recommendations) │
              │   Alembic migrations · Argon2 hashes   │
              └────────────────────────────────────────┘
```

### Key user flows

1. **Onboarding** — 8 questions ordered by **value of information** (flights and
   car first because they swing the footprint the most). The questionnaire is
   server-defined so the renderer and estimator can't drift. Answers autosave on
   each step (`PUT /onboarding/progress`), so a mid-flow close resumes at the
   saved step. `POST /onboarding/estimate` computes the Day-0 footprint and
   persists it as a `FootprintSnapshot` (`method=estimated`).

2. **Connect a source** — sandbox providers ([`providers.py`](backend/app/services/providers.py))
   fabricate realistic UK transactions or daily meter reads keyed by user UUID.
   Real GoCardless / DCC adapters drop in behind the same `Protocol`. Ingestion
   is **idempotent** (`on_conflict_do_nothing` on the natural key), data lands
   in partitioned `raw_*` tables.

3. **Recompute** — [`bank_sync.recompute_footprint`](backend/app/services/bank_sync.py)
   merges signals with precedence **activity > spend > imputed > estimated**,
   carrying the right `confidence` for each category. For energy it prefers
   metered kWh × time-of-use grid intensity. For spend it applies the R2
   merchant multiplier + price-elasticity. When the bank is connected but a
   category has no direct transactions, the R1 imputation branch fires and the
   category is flagged `imputed=true`.

4. **Insights** — the dashboard reads the cached snapshot; Insights additionally
   calls `GET /footprint/attribution` to fetch the R3 split. The bar chart shows
   sorted category breakdowns with their method/imputed badges; "What's behind
   your changes" credits the user only for the **behavioral** share.

5. **Community benchmark** — k-anonymity drops cohort size below threshold,
   R4 IPW lifts the eco-skewed mean toward the population, and a per-cohort
   Laplace draw makes the released mean (ε)-differentially private.

### Tech stack at a glance

| Layer | Stack |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript (strict), Tailwind, React Three Fiber, Zustand |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, Argon2 + PyJWT |
| Database | PostgreSQL 16, partitioned high-volume tables, JSONB snapshot payloads |
| Auth | OAuth2 password grant → short JWT, browser-side token persisted in localStorage |
| Tests | pytest + httpx ASGI client (25 cases covering R0–R4 + auth/onboarding) |

### Running locally

Detailed steps in [`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md). TL;DR (Windows / PowerShell):

```powershell
# 1) one-shot DB provisioning
cd backend
psql -h 127.0.0.1 -U postgres -d postgres -f scripts/provision_db.sql

# 2) backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # set USE_DB=true, DATABASE_URL=postgresql+asyncpg://carbonizer:carbonizer@127.0.0.1:5432/carbonizer
alembic upgrade head
python -m app.db.seed_db
uvicorn app.main:app --reload    # http://localhost:8000

# 3) frontend (in another shell)
cd ..\frontend
copy .env.local.example .env.local
npm install
npm run dev                      # http://localhost:3000
```

---

## 4. Assumptions made

We were deliberate about what's **real engineering** vs. **MVP standing in for
production data sources** so a hackathon judge / reviewer can see the difference.

### Architecture assumptions

- **Sandbox providers for ingestion.** Open Banking and smart-meter integrations
  cost money and require live OAuth registrations. We built `SandboxBankProvider`
  and `SandboxMeterProvider` behind a `Protocol` so a real GoCardless / TrueLayer /
  Octopus / DCC adapter implementing the same `fetch_*` method **drops in with no
  pipeline changes**. The downstream (idempotency, normalization, recompute) is
  production-shaped.
- **Sandbox data is deterministic per user.** Seeded by user UUID so the same
  user keeps the same fake history across runs, but two different users get
  different histories — verifying the per-user wiring without an external service.
- **No mobile app.** Background telematics needs native code (CoreMotion /
  Activity Recognition). The DESIGN.md spec describes the Rust+UniFFI core; this
  build is web-only by design.

### Modeling assumptions (and the seams where ML replaces heuristics)

- **R0 — VoI ordering** uses the *footprint spread* a question induces (varying
  it with all others at defaults). The proper version would use **expected
  information gain on R1's posterior** and re-rank adaptively as the user
  answers. The seam: a single `_question_spread` function.
- **R1 — bank-as-hub blend weights** (`prior × (0.6 + 0.4 × signal)`) are
  hand-set, not learned. The proper version learns
  `P(energy, transport | spend, demographics)` on the anchor set of users who
  connect all three sources. The seam: `impute.impute_from_bank()` — the call
  signature stays.
- **R2 — merchant priors** are a hand-curated table (~15 brands). The proper
  version learns per-merchant intensities from population spend distributions
  + a name-embedding model. Same for the per-category **price elasticities** —
  picked from plausible economics, not estimated. The seams:
  `_MERCHANT_MULTIPLIER` and `_CATEGORY_PRICE_ELASTICITY`.
- **R3 — attribution** does the exact index decomposition for **energy only**
  (electricity decomposes into grid × usage; gas is wholly behavioral). It
  doesn't yet decompose weather, price elasticity, or per-nudge causal effects
  (the doc calls for stepped-wedge rollouts + synthetic controls — explicitly
  future work).
- **R4 — IPW lift** uses a constant **+10% selection skew** as a stand-in for
  per-cohort propensity scores. The DP mechanism (Laplace, ε=1, sensitivity=0.1)
  is real and deterministic per cohort, so repeated reads don't re-leak. Real
  rollout would use **secure aggregation** for cohort statistics and learned
  propensities.

### Numerical assumptions

- **Carbon factors** are DEFRA / EEA-style order-of-magnitude figures
  (gCO₂/km for transport modes, kgCO₂e/£ EIO-LCA intensities, kgCO₂e/kWh for
  gas, live grid intensity for electricity). They're intentionally rough so the
  ladder activity → spend → imputed → estimated is meaningful; the proper
  factor set lives in databases like Climatiq / EXIOBASE 3.11 / ecoinvent.
- **Currency** assumed GBP throughout the MVP, region = "GB". International
  expansion (EU then US) is a roadmap item — see DATA-STRATEGY.md §8.
- **Recompute window** is 12 weeks (~84 days), annualized for the headline
  total. Range parameter accepts `12w | 6m | 1y` but only `12w` has a snapshot
  cache today.

### Auth & data assumptions

- **Argon2id** for password hashes (real, not a stand-in).
- **JWT access tokens** held in `localStorage` for the MVP. The backend already
  issues refresh tokens as `HttpOnly` cookies; the frontend will move to them
  before any real users.
- **k-anonymity threshold k=50** for cohort size suppression (hardcoded).
- **No real PII connectors.** All "connect" buttons run the sandbox provider;
  nothing leaves your machine.

### What's intentionally out of scope for this build

- Real Open Banking aggregator (GoCardless / TrueLayer / Plaid).
- Real smart-meter integration (Octopus OAuth / DCC / n3rgy).
- Mobile telematics SDK.
- NLP transaction classifier (the docs cite a fine-tuned RoBERTa at ~87% F1 —
  not yet in the build).
- Web3 / Personal Carbon Trading (called out in DESIGN.md §9 as optional /
  future-phase).

---

## Repository map

```
docs/                 design specs (read these for depth)
  DESIGN.md           product & architecture
  UI-UX-DESIGN.md     visual language and screens
  DB-SCHEMA.md        database design
  API-DESIGN.md       REST contract
  DATA-STRATEGY.md    real-data strategy + R0–R4 details

backend/              FastAPI service
  app/                core / db / models / schemas / services / api
  alembic/            migrations
  tests/              pytest suite
  scripts/            provisioning SQL
  README.md           detailed run guide

frontend/             Next.js + Three.js app
  src/app/            routes (App Router)
  src/components/     biome / landing / onboarding / dashboard / insights / act / profile
  src/lib/            api clients, types, hooks, design tokens
  src/store/          Zustand stores
  README.md           detailed run guide
```
