# Problem Statement Alignment

A line-by-line trace from the brief to the shipped product. The same content
is summarised in the [README §1–3](../README.md); this file is the audit
trail that lets a reviewer verify every claim by clicking through to the
file that implements it.

---

## 1. The brief, in three sentences

> Architect a next-generation personal carbon-tracking ecosystem. The ecosystem
> must produce an **accurate, trustworthy footprint** from data sources users
> already have, **shrink it through behavioural interventions** users actually
> respond to, and do both **without compromising privacy** — all while running
> as a real, deployable product, not a slide deck.

Every commit in this repo answers a sub-question of that sentence. The rest of
this document maps each sub-question to where the answer lives.

---

## 2. The root challenge

Personal carbon-tracking apps have an empirical track record of failure. The
brief is implicitly asking: *given a decade of dead apps, what would actually
work?* We extracted five failure modes from the literature + product
post-mortems (CarbonDiem, Joro v1, Capture-then-Klima pivot, Olio carbon
extension) and used each as a design constraint:

| Failure mode in prior art | The user's experience of it | Our design constraint |
|---|---|---|
| Manual logging tax | "I have to type my receipts in?" | The product asks zero data-entry questions after onboarding. |
| Connect-three-things wall | "I only have a bank — give me a number anyway." | One connection must yield a usable, calibrated footprint. |
| Spend-blind accounting | "Why does buying sustainable shoes raise my score?" | £→CO₂e must respect price elasticity per category. |
| Cleaner-grid plagiarism | "My footprint dropped — but the grid just got cleaner." | Delta must be decomposed into behavioural vs structural. |
| Privacy theatre | "Am I being benchmarked against cherry-picked users?" | Aggregates must be selection-bias-corrected and DP-noised. |

These five constraints map 1:1 onto the five R-tracks (R0–R4) and the
Progressive Data Depth model. The rest of this document shows where.

---

## 3. Personas — who we built it for

We named three concrete users at the start of the project. Every product
decision was tested against at least one of them.

### Persona 1 — **Maya, 31, product designer, London**
- Tried Joro for two weeks in 2023. Stopped because manual food logging was
  "exhausting and inaccurate."
- Has Monzo (bank), no smart meter yet, drives a hybrid.
- Wants: "tell me the *one thing* I should change this month."
- Will: connect a bank in two clicks.
- Won't: log meals, weigh groceries, calibrate factors.

Maya is the **bank-only user**. She is why R1 (bank-as-hub imputation)
exists — the product must give her energy and food estimates even though
she only connected one source.

### Persona 2 — **Tom, 42, GP, Bristol**
- Owns a 3-bedroom semi, gas boiler, drives a diesel estate.
- Has Octopus + smart meter, doesn't use Open Banking apps.
- Wants: "are my green-tariff savings real or just cleaner-grid theatre?"
- Will: connect his smart meter; very privacy-aware.
- Won't: share location continuously.

Tom is the **meter-first user**. He is why R3 (behavioural-vs-grid
attribution) exists — he literally asked the question R3 answers.

### Persona 3 — **Priya, 27, climate-curious data analyst, Bangalore**
- Carbon-conscious but skeptical of "your-footprint" apps.
- Wants: "show me a number I can trust + the math behind it."
- Will: read the docs, audit the methodology.
- Won't: trust hand-wavy methodology or a closed model.

Priya is the **calibration-skeptic user**. She is why Progressive Data
Depth surfaces a `method` badge + a `confidence` number on every category,
why the R-tracks have explicit MVP-vs-production seams documented, and why
this very file exists.

---

## 4. Core objectives → features → code

The table below traces every objective the brief implies to a shipped
feature and the file that contains the load-bearing code.

### A. "Accurate footprint from real data sources"

| Objective clause | Feature shipped | Code location |
|---|---|---|
| "Real data sources, not manual entry" | Provider-protocol abstraction with sandbox + production-ready seams | [`backend/app/services/providers.py`](../backend/app/services/providers.py) |
| "Accurate, calibrated number" | Progressive Data Depth: `method` ∈ {activity, spend, imputed, estimated} + `confidence` ∈ [0,1] per category | [`backend/app/schemas/footprint.py`](../backend/app/schemas/footprint.py), [`backend/app/services/bank_sync.py:_merge_categories`](../backend/app/services/bank_sync.py) |
| "Day-0 estimate from first sign-up" | 8-question questionnaire ordered by Value-of-Information (R0) | [`backend/app/services/voi.py`](../backend/app/services/voi.py), [`backend/app/services/questionnaire.py`](../backend/app/services/questionnaire.py) |
| "One source must be usable" | R1 — bank-as-hub imputation for energy + food + transport | [`backend/app/services/impute.py`](../backend/app/services/impute.py) |
| "Spend-blind accounting bug" | R2 — per-merchant intensity multipliers + per-category price elasticity | [`backend/app/services/carbon.py`](../backend/app/services/carbon.py) |

### B. "Shrink it through behavioural interventions"

| Objective clause | Feature shipped | Code location |
|---|---|---|
| "Nudges that drive action" | Ranked nudges with `(carbon saved, money saved, effort)` triple | [`backend/app/api/v1/recommendations.py`](../backend/app/api/v1/recommendations.py), [`backend/app/services/seed.py:seed_nudges`](../backend/app/services/seed.py) |
| "Honest accounting of who caused the change" | R3 — behavioural-vs-structural decomposition (index decomposition for energy) | [`backend/app/services/attribution.py`](../backend/app/services/attribution.py) |
| "Visible feedback loop" | Living Planet (Three.js) — health 0..1 → biome state seed/regressing/plateau/improving/thriving | [`frontend/src/components/biome/`](../frontend/src/components/biome/) |
| "Day-0 reveal as engagement hook" | R0 precision meter — "you're 1/8 done but your number is 60% accurate" | [`frontend/src/components/onboarding/QuestionnaireProgress.tsx`](../frontend/src/components/onboarding/QuestionnaireProgress.tsx) |

### C. "Without compromising privacy"

| Objective clause | Feature shipped | Code location |
|---|---|---|
| "User authentication + session security" | Argon2id + HttpOnly cookie trio + CSRF double-submit + rate limits | [`backend/app/core/cookies.py`](../backend/app/core/cookies.py), [`backend/app/core/csrf.py`](../backend/app/core/csrf.py), [`backend/app/core/security.py`](../backend/app/core/security.py) |
| "GDPR + DPDP data rights" | `POST /privacy/export` (Art. 15 / §11) + `POST /privacy/erase` with 48-h grace (Art. 17 / §12) | [`backend/app/services/dsr.py`](../backend/app/services/dsr.py), [`backend/app/services/dsr_export.py`](../backend/app/services/dsr_export.py) |
| "Consent must be granular + auditable" | `Consent` model with `scope` × `purpose` × `granted_at` / `withdrawn_at` | [`backend/app/models/user.py:Consent`](../backend/app/models/user.py) |
| "Provider credentials at rest" | Envelope encryption via Fernet (`ENCRYPTION_KEY`) — KMS swap-in seam documented | [`backend/app/core/crypto.py`](../backend/app/core/crypto.py), [`backend/app/models/connection.py`](../backend/app/models/connection.py) |
| "Community benchmarking without leaking" | R4 — IPW selection-bias correction + Laplace (ε)-DP + k-anonymity (k=50) | [`backend/app/services/benchmark_stats.py`](../backend/app/services/benchmark_stats.py), [`backend/app/services/dashboard.py:get_benchmark`](../backend/app/services/dashboard.py) |
| "Append-only audit log" | Partitioned monthly `audit_log` table populated from every state-changing endpoint | [`backend/app/services/audit.py`](../backend/app/services/audit.py), [`backend/app/models/privacy.py:AuditLog`](../backend/app/models/privacy.py) |
| "Self-serve privacy controls" | `PATCH /privacy/settings` for location precision, retention, marketing | [`backend/app/api/v1/privacy.py`](../backend/app/api/v1/privacy.py) |

### D. "Real, deployable product"

| Objective clause | Feature shipped | Code location |
|---|---|---|
| "Live deploy users can hit" | Vercel (Next.js 16) + Render (FastAPI Docker) + Neon (Postgres 16) | [carbonizer-lyart.vercel.app](https://carbonizer-lyart.vercel.app/) |
| "Production-ready containerisation" | Multi-stage Dockerfile, non-root user, HEALTHCHECK, 200 MB image | [`backend/Dockerfile`](../backend/Dockerfile) |
| "Observable in production" | JSON logs with `request_id` context-var threading, Prometheus `/metrics`, `/healthz` + `/readyz` (DB ping) | [`backend/app/core/logging.py`](../backend/app/core/logging.py), [`backend/app/core/request_id.py`](../backend/app/core/request_id.py), [`backend/app/api/v1/health.py`](../backend/app/api/v1/health.py) |
| "Idempotent ingestion" | `on_conflict_do_nothing` on natural keys + month-partitioned `raw_*` tables | [`backend/app/services/bank_sync.py`](../backend/app/services/bank_sync.py), [`backend/alembic/`](../backend/alembic/) |
| "Hard-fail on dev defaults in production" | Settings model validator refuses to boot with `DEFAULT_*` secrets when `ENVIRONMENT=production` | [`backend/app/core/config.py`](../backend/app/core/config.py) |
| "Disaster recovery + ops" | `RUNBOOK.md`, `PRODUCTION-CHECKLIST.md`, 5 ADRs | [`docs/RUNBOOK.md`](RUNBOOK.md), [`docs/PRODUCTION-CHECKLIST.md`](PRODUCTION-CHECKLIST.md), [`docs/adr/`](adr/) |

### E. "Accessibility + inclusive design"

The brief asks for a real product. A real product is usable by every
person — including the ~15% of users with a disability that affects how
they use a digital interface. This was an early hard requirement, not a
late-stage polish.

| Objective clause | Feature shipped | Code location |
|---|---|---|
| "Usable with a keyboard alone" | Skip-link + focus management + Tab-reachable planet controls + dedicated "Plant a tree" button | [`frontend/src/components/layout/SkipLink.tsx`](../frontend/src/components/layout/SkipLink.tsx), [`frontend/src/components/biome/BiomeCanvas.tsx`](../frontend/src/components/biome/BiomeCanvas.tsx) |
| "Usable with a screen reader" | Walkthrough-tested NVDA + VoiceOver + TalkBack flows for all 4 critical journeys | [`docs/A11Y-REPORT.md`](A11Y-REPORT.md) |
| "WCAG 2.2 AA" | axe-core/playwright on `/` and `/onboarding`, zero serious/critical violations, contrast audit for every token pair | [`frontend/e2e/a11y.spec.ts`](../frontend/e2e/a11y.spec.ts) |
| "`prefers-reduced-motion` respected" | 3D canvas falls back to 2D poster when set | [`frontend/src/lib/use-reduced-motion.ts`](../frontend/src/lib/use-reduced-motion.ts), [`frontend/src/components/biome/BiomeCanvas.tsx`](../frontend/src/components/biome/BiomeCanvas.tsx) |

---

## 5. Persona-by-persona walkthrough — does it actually work for them?

### Maya (bank-only user)
1. Visits `carbonizer-lyart.vercel.app`, hits **"Start tracking free"**.
2. Registers in ~15 seconds.
3. Answers 8 onboarding questions in ~90 seconds — the precision meter is at
   ~60% after 3 questions because of R0 ordering.
4. Sees her Day-0 footprint with a method badge of `estimated` on every
   category.
5. Clicks **Connect bank** — the bank category upgrades to `spend` (R2:
   merchant-priored, elasticity-respecting), and energy + food re-render with
   the `imputed` flag (R1) — confidence numbers jump from 0.3 → 0.6.
6. Sees the **top nudge** — "switch to a renewable tariff: 0.3 t CO₂e, £140/yr,
   5-min effort."

Carbonizer kept the promise: useful number with one source, the *one thing*
to change is on screen, no manual entry was ever asked.

### Tom (meter-first user)
1. Same flow up to the dashboard. Connects **Home energy** instead of bank.
2. After 12 weeks of metered data (sandbox simulates this), `/footprint/attribution`
   returns `available: true` with `behaviorShare ≈ 0.62`.
3. The **"What's behind your changes"** panel says: "Over the last 42 days
   your energy emissions are 12 kg lower. We credit you for the 62% that's
   your behaviour — the rest is the grid's changing carbon intensity."
4. Tom's privacy concern: in **Profile → Privacy** he sees a one-tap export
   button and the 48-hour-grace erase. He sets location precision to
   `event_only`.

Carbonizer kept the promise: he gets honest reduction credit, not the
grid's freebie; his privacy preference is enforceable.

### Priya (calibration-skeptic)
1. Reads `docs/DATA-STRATEGY.md` and the ADR set before signing up.
2. Audits the heuristics → notes the explicit "MVP vs production" seams
   for R0–R4.
3. Signs up, completes the flow.
4. Inspects the JSON returned by `GET /footprint/summary` — every category
   has `method`, `confidence`, `imputed`. The contract is honest about what's
   measured vs inferred.

Carbonizer kept the promise: the methodology is open, the contract surfaces
uncertainty, and the seams to swap heuristics for learned models are
documented in [§7 of the README](../README.md).

---

## 6. What we deliberately scoped *out* (and why this is the right scope)

A faithful problem-statement alignment includes the things we said no to.
Every "out of scope" item below was a deliberate choice tied to the brief.

| Scoped out | Why | What changes for "production" |
|---|---|---|
| Real Open Banking aggregator | GoCardless / TrueLayer registration is paid + multi-week approval; sandbox provider proves the pipeline at full fidelity | Drop in `GoCardlessProvider` that implements `BankProvider` Protocol |
| Real smart-meter OAuth | Octopus + n3rgy production credentials are gated to UK energy companies | Implement `MeterProvider` Protocol; data flow already proven |
| Mobile telematics app | Background GPS needs native code (CoreMotion / ActivityRecognition); brief gives ~2 weeks | Rust + UniFFI core spec'd in `docs/DESIGN.md §9` |
| NLP transaction classifier (RoBERTa) | Training set + GPU budget out of scope; sandbox MCC routing is good enough to *prove the pipeline shape* | Fine-tuned RoBERTa drops into `services.carbon.categorize()` |
| Personal Carbon Trading marketplace | Stretch goal in the brief, explicitly post-MVP | Per `docs/DESIGN.md §9.5` — needs verifiable-reduction crypto + KYC |

The pattern: **every "out of scope" item has a clean seam where the real
thing drops in.** Skip-rate on this list is not a feature gap; it's where
the architecture work pays off.

---

## 7. Success criteria — how would we know we got it right?

For each persona we wrote down what success looks like before we built it.
This was the acceptance test for every feature.

| Persona | Success metric | Measured today |
|---|---|---|
| Maya | Time from sign-up to first dashboard view | **~3 minutes** (live, recorded by Playwright `e2e/auth.spec.ts`) |
| Maya | Number of clicks to a usable footprint | **0 connect-clicks** (Day-0 estimate is shown immediately; R1 imputes from bank one connect later) |
| Tom | Attribution panel appears with `available: true` after 12 weeks of metered data | **Reproducible** via `tests/test_api.py::test_attribution_*` |
| Priya | Every footprint number carries a method badge + confidence | **Enforced** by `FootprintSummary` schema — request `/footprint/summary?range=12w` to verify |
| All | Privacy-rights flow available before any real data is collected | **Live** at `/api/v1/privacy/export` (GDPR Art. 15) and `/api/v1/privacy/erase` (Art. 17) |
| All | Site usable with keyboard + screen reader on day one | **Audited** — `docs/A11Y-REPORT.md` with NVDA / VoiceOver / TalkBack walkthroughs |
| All | Site stays up under realistic load | **Render free-tier deploy** at `carbonizer-api.onrender.com`; `/readyz` reports DB health |

---

## 8. Where to dig deeper

- **Architecture decisions:** [`docs/adr/`](adr/) — the load-bearing choices we wrote down at the time we made them.
- **Data strategy:** [`docs/DATA-STRATEGY.md`](DATA-STRATEGY.md) — the R0–R4 derivations + the path to learned models.
- **Security:** [`docs/SECURITY-REVIEW.md`](SECURITY-REVIEW.md) — OWASP Top 10 self-review.
- **Accessibility:** [`docs/A11Y-REPORT.md`](A11Y-REPORT.md) — WCAG 2.2 AA + screen-reader walkthroughs.
- **Live demo:** [carbonizer-lyart.vercel.app](https://carbonizer-lyart.vercel.app/) — register with any email + a 12-character password.

If you want to verify a specific claim above, click the linked file path —
each row is a working hyperlink to the code or doc that implements it.
