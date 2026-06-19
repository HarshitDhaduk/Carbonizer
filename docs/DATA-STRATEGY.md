# Carbonizer — Real-Data Acquisition Strategy

How Carbonizer goes from seeded/mock data to **real per-user carbon data**, balancing
accuracy against onboarding friction. Combines a product/funnel plan with the research
directions that make the hard parts work. Companion to [DESIGN.md](DESIGN.md),
[API-DESIGN.md](API-DESIGN.md), and [DB-SCHEMA.md](DB-SCHEMA.md).

---

## 1. The core reframe

The user's job-to-be-done is **"understand and shrink my footprint with near-zero
effort"** — not "connect my accounts." So data strategy is **funnel strategy**. The
metric that governs everything is **time-to-first-insight (TTFI)**. The failure mode that
kills personal carbon trackers is an empty, effortful onboarding.

Model a user's footprint as a **posterior distribution with calibrated uncertainty**:
each data source is a noisy observation that shrinks variance; each unmeasured category is
a wide prior. This single move unifies most of the strategy below.

## 2. The spine: Progressive Data Depth

Everyone starts with a Day-0 *estimate*; each connection visibly **upgrades** categories
`estimated → spend → activity` and grows the Living Planet biome. Accuracy improvement
*is* the engagement loop. The `method` badge (already in the schema) doubles as a progress
bar.

## 3. Prioritized data sources

| # | Channel | Method | Accuracy | Friction | Build vs Buy | Phase |
|---|---|---|---|---|---|---|
| 1 | **Onboarding questionnaire** (household, home, diet, car, flights) | estimated | Low | **Very low** | **Build** | MVP |
| 2 | **Open Banking** via aggregator (GoCardless free tier → TrueLayer/Tink) | spend | Low–Med | Medium | **Buy** | MVP |
| 3 | **Manual flights** (episodic, high-impact) | activity | High | Low | **Build** | MVP/P1 |
| 4 | **Smart meter / energy** (Octopus OAuth, n3rgy/Glow-DCC; bill OCR fallback) | activity | High | High | **Buy** | P2 |
| 5 | **Transport import** (Google Timeline, Apple Health/Fit, Strava) | activity | Med–High | Medium | **Buy/Build** | P2 |
| 6 | **Native telematics SDK** (bg motion+GPS; Tracelet-style / Sentiance) | activity | High | High (needs mobile app) | **Buy SDK** | P3 |
| 7 | Product-level PCF (receipts / e-commerce) | spend→item | Med | High | Build | P4 |

**Buy the pipes, build the brain.** Integrate ingestion (aggregators, SDKs); the moat is
the accounting engine + behavioral UX + biome.

## 4. MVP scope

Ship **#1 + #2 (+ #3)** on the existing web stack — no mobile app required:

1. **Questionnaire → Day-0 footprint** (`method=estimated`). The biome is never empty.
2. **One Open Banking aggregator, UK-first** → spend-based baseline; upgrades most
   categories `estimated → spend`.
3. **Manual flight entry** — captures the biggest swings spend-based data misses.

Deliberately **defer** energy (P2) and native telematics (P3): highest friction, lowest
coverage, and telematics requires a mobile app we don't yet have.

> **Implementation status:** Step 1 (the onboarding estimator) is the first slice being
> built — see §8.

## 5. Key tradeoffs

- **Accuracy ↔ friction** — resolved by Progressive Data Depth, not by choosing one.
- **Spend-based is blunt** — same MCC for fast-fashion vs sustainable brand. Accept for
  MVP; fix with R2 (below).
- **Web ↔ mobile** — telematics forces native; keep MVP web. "Build the mobile app" is an
  explicit, dated decision gated on transport proving a retention lever.
- **Build ↔ buy** — buy ingestion, build the downstream.

## 6. Risks → mitigations

| Risk | Mitigation |
|---|---|
| Bank-connect drop-off (#1 funnel leak) | Questionnaire first → show value → then ask; "read-only, we never move money" |
| Aggregator cost scaling | Free tier first; cache; respect PSD2 90-day re-consent |
| "That number's wrong" → trust loss | Let users exclude/recategorize; show the `method` badge |
| GDPR/DPDP (financial + location sensitive) | Purpose limitation, minimization, on-device where possible, frictionless withdrawal/erasure |
| Low coverage (smart meter / telematics) | Sequence late; bill-upload / import fallbacks |

## 7. Success metrics

- **North Star:** *% of a user's footprint that is **measured** (spend/activity) vs
  estimated*, among weekly-active users — quality **and** engagement in one number.
- **Activation:** % completing the questionnaire (Day-0 footprint) — target **>70%**.
- **Connection rate:** % connecting ≥1 bank within 7 days — target **>30%**.
- **TTFI:** time to first footprint **< 2 min**.
- **Depth:** measured categories / 5; correlate with W4 retention.
- **Outcome:** median footprint Δ at 90 days; nudge-acceptance rate.
- **Privacy health:** consent-withdrawal rate, DSR SLA adherence.

## 8. Phased roadmap & geography

- **P0 (MVP):** questionnaire + 1 Open Banking aggregator + manual flights, **UK-first**.
- **P1:** transaction-categorization quality (NLP), correction UX, real-spend recommendations.
- **P2:** energy (Octopus/n3rgy/Glow + bill OCR); transport imports.
- **P3:** mobile app + native telematics.
- **P4:** product-level PCF; PCT/Web3 experiments.
- **Geo:** UK → EU (same aggregator, PSD2) → US (Plaid + Green Button, new factor sets).

---

## 9. Research directions (the hard, differentiating problems)

Each is **validatable on public datasets before we have users** — UK *Living Costs & Food
Survey* / US *Consumer Expenditure Survey* for spend↔category↔energy↔travel joints;
*UK-DALE / Low Carbon London / Pecan Street* + National Grid *Carbon Intensity API* for
energy; *EXIOBASE/DEFRA* factors.

### R1 — Open Banking as a "hub view": impute unmeasured categories *(Tensions: coverage + friction)*
Most users connect only their bank, but bank data already partially observes the other
categories (a fuel transaction implies driving; an energy direct-debit implies kWh; a
flight purchase implies aviation). Learn `P(energy, transport | spend, demographics)` on
the minority who connect all three (the **anchor set**), then reconstruct unmeasured
categories for single-source users — with uncertainty, surfaced via the `method` badge.
*Novel:* multi-view learning where the bank is a noisy projection of the other views;
use the multi-connected minority to de-bias the single-connected majority.
*Validate:* hold out a view on survey data; error vs cohort-average baseline.
**Implemented (MVP):** `backend/app/services/impute.py` + a calibrated `confidence`
(0..1) on every category (`activity 0.95 > spend 0.80 > imputed 0.55 > estimated
0.30`). When the bank is connected but a category has no transactions (e.g. energy —
which belongs to the smart meter), it's reconstructed from the bank's total-spend
"hub" signal and surfaced as an **"Inferred"** badge until measured. The blend
weights are the seam where an anchor-set-learned model drops in.

### R0 — Value-of-Information onboarding *(composes with R1)*
Instead of a fixed funnel, ask the next question/connection that most reduces footprint
uncertainty per tap (optimal experimental design). R1's posterior drives the order.
*Validate:* adaptive vs fixed question order; footprint-error vs #-taps curve.
**Implemented (MVP):** `backend/app/services/estimator.py` scores each question's VoI by
the total-footprint spread its answers induce, then orders questions highest-yield first
(dependency-respecting, so a gated question follows its parent). The questionnaire shows
an **"Estimate precision"** meter (cumulative answered VoI) that climbs far faster than
step progress — e.g. ~57% after the first (flights) question — visualizing that the
footprint sharpens most from the first few taps. Full adaptive re-ranking on R1's live
posterior is the next layer.

### R2 — Break the price↔carbon proportionality assumption *(Tension: spend-based blindness)*
Spend-based accounting assumes carbon ∝ price, so paying more for a sustainable product
wrongly inflates the footprint. Learn (a) merchant-carbon priors from population spend +
merchant-name embeddings to discriminate eco vs non-eco within an MCC, and (b) a per-
category price-elasticity-of-carbon correction. *Validate:* rank same-MCC merchant pairs
of known sustainability tiers (ranking AUC) vs the MCC baseline that ties them.
**Implemented (MVP):** `backend/app/services/carbon.py` — a curated merchant→intensity
multiplier (green energy / sustainable / second-hand below 1.0; fast-fashion above) and
a per-category price-elasticity `co2e = factor·ref·(gbp/ref)^e` so premium spend
decouples from carbon (e<1 for goods, e=1 for fuel/energy). The curated table is the
placeholder for population-learned merchant priors.

### R3 — Honest reduction attribution: structural vs behavioral *(Tension: causal credit)*
A footprint drop may be the grid greening, weather, or price — not behavior. Decompose
ΔCO₂e into grid-intensity / weather / price / **behavioral residual**, and estimate nudge
effects with **stepped-wedge randomized rollouts + per-user synthetic controls**. Credit
the user only for the residual — what makes the gamification trustworthy. *Validate:*
smart-meter data + Carbon Intensity API; placebo tests; synthetic-control vs naive pre/post.
**Implemented (MVP):** `backend/app/services/attribution.py` + `GET /footprint/attribution`
— splits the metered window into prior/current halves and decomposes energy ΔCO₂e by
index decomposition into **behavioral** (usage × old grid) and **structural** (new usage
× grid change), which sum exactly to the true Δ. The Insights page shows the
behavior-vs-grid split and credits the user only for the behavioral share. Weather/price
terms and synthetic-control nudge effects are the next layer.

### R4 — Privacy-preserving + selection-bias-corrected benchmarking *(Tension: privacy)*
Benchmarks need population stats without exposing anyone, and the users who connect data
are self-selected (eco-skewed). On-device classification (RWKV/edge) + **federated learning
with secure aggregation / DP** for cohort means, plus **MNAR selection-bias correction**
(inverse-propensity reweighting) so "you're below average" reflects the real population.
*Validate:* ε vs benchmark-accuracy Pareto; IPW recovering true mean from an eco-skewed sample.
**Implemented (MVP):** `backend/app/services/benchmark_stats.py` — IPW lifts the eco-skewed
connector mean toward the true population, then a **Laplace (ε)-DP** mechanism releases it
(deterministic per cohort, so it doesn't re-leak each read); k-anonymity already suppresses
small cohort sizes. "You vs average" compares against the corrected mean, and the gauge is
labelled **"Privacy-protected · adjusted for who connects."** The skew factor is the seam
for learned propensity scores; secure aggregation replaces the central mean later.

### Headline thesis
*Personal carbon apps fail because accuracy demands effort users won't give, leaving
footprints mostly unmeasured and reductions unattributable. Carbonizer models the footprint
as a calibrated posterior where Open Banking acts as a hub that partially observes all
categories, uses value-of-information to ask only the highest-yield onboarding step, and
decomposes reductions into structural vs behavioral so credit is honest.*
