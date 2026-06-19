# Carbonizer — Design Document

> A next-generation personal carbon tracking ecosystem that moves users from passive
> environmental awareness to active, measurable mitigation through automated data
> ingestion, scientifically rigorous carbon accounting, and behaviorally-informed
> feedback loops.

---

## 1. Vision & Problem Statement

Household consumption and personal lifestyle choices account for a substantial
majority of global greenhouse gas (GHG) emissions, yet most regulatory attention
targets corporate and governmental actors. Carbonizer closes this gap by giving
individuals a frictionless, accurate, and motivating way to understand, track, and
reduce their carbon footprint.

The core challenge is twofold:

1. **Eliminate the friction of manual data entry** that drives high user attrition and
   poor data quality in legacy self-reporting apps.
2. **Maintain rigorous scientific accuracy** while overcoming the cognitive biases that
   inhibit sustainable behavior.

Carbonizer is built as a convergence of six disciplines: carbon accounting,
automated data ingestion, behavioral economics, machine learning, decentralized
systems, and data-privacy engineering.

### Design Principles

- **Automated over manual.** Deprecate self-reporting in favor of deterministic,
  continuous data streams.
- **Activity-based where possible, spend-based where necessary.** Prefer direct
  physical measurement; fall back to economic estimation for coverage.
- **Green by construction.** The tracking infrastructure must not exacerbate the crisis
  it seeks to mitigate ("Green AI").
- **Privacy by design.** Consent-driven, purpose-limited, and minimization-first.
- **Behaviorally grounded.** Use choice architecture to close the intention–action gap.

---

## 2. Carbon Accounting Engine

The accounting core aligns with established international frameworks: the IPCC
guidelines, the GHG Protocol, and localized emission databases such as the UK's
DEFRA factors.

### Unit of Measurement

All emissions are normalized to **Carbon Dioxide Equivalent (CO₂e)**, standardizing the
Global Warming Potential (GWP) of multiple gases over a 100-year horizon.

**Baseline equation:**

```
GHG emissions = activity data × emission factor × GWP
```

### Why Not Ecological Footprint?

The legacy Ecological Footprint model (global hectares vs. biocapacity) breaks down at
the household scale — weak data availability, broad assumptions, and difficulty
accounting for edge cases (e.g., biocapacity loss from nuclear exclusion zones).
Carbonizer therefore defaults to **GHG Protocol scope-based tracking**.

### Two Quantification Modalities

| Methodology | Mechanism | Inputs | Strengths | Limitations |
|---|---|---|---|---|
| **Activity-Based** | Direct measurement of physical consumption | Liters of fuel, kWh, km traveled, mass of goods | Highest precision; aligns with IPCC Tier 1/2/3 | Requires granular telemetry & deep hardware/utility integration |
| **Spend-Based** | Economic input-output LCA (EIO-LCA) | Transaction amount, currency, industry classification | Highly scalable; works with Open Banking | Distorted by price volatility; can't distinguish identically-priced eco products |

Carbonizer uses **activity-based tracking as the gold standard** and **spend-based
estimation for breadth of coverage**, reconciling the two per category.

---

## 3. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION                           │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────────────┐   │
│  │ Open       │   │ Mobile       │   │ Smart Grid / Utility  │   │
│  │ Banking    │   │ Telematics   │   │ Meter APIs            │   │
│  │ (PSD2)     │   │ (Edge SDK)   │   │ (DCC / Octopus)       │   │
│  └─────┬──────┘   └──────┬───────┘   └──────────┬───────────┘   │
└────────┼─────────────────┼──────────────────────┼───────────────┘
         │                 │                      │
┌────────▼─────────────────▼──────────────────────▼───────────────┐
│                    CARBON ACCOUNTING ENGINE                      │
│   NLP transaction classification · Emission-factor mapping       │
│   Activity↔Spend reconciliation · CO₂e normalization             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│              INTELLIGENCE & RECOMMENDATION LAYER                  │
│   Green-AI recommender systems · Forecasting (LSTM)              │
│   Multi-objective optimization (NSGA-II / GA)                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│            BEHAVIORAL & PRESENTATION LAYER                        │
│   Green nudges · Social benchmarking · Gamification · Equivalents │
└──────────────────────────────────────────────────────────────────┘

   Cross-cutting: Privacy-by-Design · Optional Web3 / PCT settlement
```

---

## 4. Financial Ingestion & Transaction Classification

### Open Banking Integration

Under PSD2 (Europe) and equivalent regimes, Carbonizer ingests user transaction
histories via authorized third-party access. Raw transactions are then mapped to
carbon equivalents.

### Tiered Estimation Strategy

1. **MCC-based baseline (broad coverage).** Merchant Category Code lookups (e.g.,
   Mastercard / Doconomy Åland Index style) provide instant footprint estimates from
   transaction amount + MCC. **Limitation:** MCCs are blunt — a fast-fashion retailer
   and a sustainable brand sharing an MCC yield identical footprints, penalizing good
   choices.

2. **Scientifically-vetted factors (high granularity).** A deeper API such as
   **Climatiq** (1M+ emission factors from 140+ databases — ecoinvent, EXIOBASE 3.11,
   IEA, sustamize) supplies ISO 14067 / GHG-Protocol-compliant estimates.

#### Climatiq Procurement API — key fields

| Component | Parameter | Function |
|---|---|---|
| Request | `spend_region` | UN/LOCODE of expenditure region — localizes emission factors |
| Request | `tax_margin` | Tax contribution to final purchaser price |
| Request | `trade_margin` | Trade contribution (EXIOBASE defaults if omitted) |
| Response | `co2e_calculation_method` | e.g. `ipcc_ar4_gwp100`, `ipcc_ar5_gwp100`, `ipcc_ar6_gwp100` |
| Response | `direct_emissions` | Direct combustion/generation (incl. radiative forcing for air travel) |
| Response | `indirect_emissions` | Upstream (transmission losses, well-to-tank) |

### NLP-Based Classification

To bridge raw, unstructured bank descriptions to precise emission factors,
Carbonizer applies a **domain-adapted NLP classifier** mapping transactions to
commodity classes / product carbon footprints (PCFs).

Benchmark targets (from literature):

| Approach | F1 |
|---|---|
| Zero-shot classification | 40.1–43.7% |
| TF-IDF | ~69% |
| Word2Vec | ~72% |
| **Fine-tuned RoBERTa-base** | **87.2%** |

A fine-tuned transformer model is the target classifier, enabling Carbonizer to
**override generic MCCs** with semantically-matched, product-specific footprints.

---

## 5. Geospatial Telematics & Mobile Edge Computing

Transportation is frequently the largest single segment of a personal footprint.
The challenge: continuous background geolocation drains battery and drives uninstalls.

### Power-Efficient Tracking

- **Hardware-accelerated Activity Recognition** (CoreMotion on iOS, Activity
  Recognition API on Android) detects transport mode from the accelerometer **before**
  activating GPS.
- **Adaptive sampling** driven by three simultaneous signals — activity type, battery
  level, and speed elasticity:

  | State | Distance Filter |
  |---|---|
  | Stationary | 500 m (GPS effectively paused) |
  | Walking | 50 m |
  | Driving (highway) | 10 m (captures curvature) |
  | Battery < 10% | all filters × 5 |

- **Extended Kalman Filter** on every fix to smooth GPS drift. State vector
  `[x, y, vₓ, v_y]` (position + velocity in meters), with automatic process-noise
  adjustment to accommodate fix gaps.

### Cross-Platform Core

Complex logic — geofence ray-casting, proximity evaluation, SQLite persistence — is
centralized in a **shared Rust core bridged via UniFFI** to Swift and Kotlin. This
guarantees mathematical/behavioral parity across iOS and Android and avoids
garbage-collected background overhead (architectural pattern modeled on the
open-source Tracelet engine).

### Emission Calculation

Once mode + distance are isolated, emissions use standard factors (e.g. EU EEA 2024):

| Mode | gCO₂/km |
|---|---|
| Passenger car | 192 |
| Bus | 89 |
| Train | 41 |
| Cycling / Walking | 0 |

---

## 6. Smart Infrastructure & Utility Integration

Household energy moves from static monthly approximations to exact, time-of-use,
activity-based tracking.

- **Smart meter backbone.** In digitized grids (e.g., UK), Meter Asset Managers (MAMs)
  and the central Data Communications Company (DCC) transmit real-time usage to
  authorized apps.
- **Reference API (Octopus Energy REST).** HTTP Basic Auth with an API key:

  | Resource | Method | Path |
  |---|---|---|
  | Electricity meter point | GET | `electricity-meter-points/{mpan}/` |
  | Electricity consumption | GET | `electricity-meter-points/{mpan}/meters/{serial_number}/consumption/` |
  | Gas consumption | GET | `gas-meter-points/{mprn}/meters/{serial_number}/consumption/` |
  | Tariff standard rates | GET | `products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/` |

- **Time-of-use carbon.** Half-hourly consumption (down to 0.001 kWh) is mapped against
  the **real-time carbon intensity** of the local grid.
- **Dual incentive.** Because grid prices are lowest when renewable generation is
  highest, syncing financial cost with carbon cost lets Carbonizer proactively nudge
  users to shift high-load activities (EV charging, heat pumps) to off-peak, low-carbon
  windows — cutting both bills and emissions.

---

## 7. Intelligence & Recommendation Layer

### Multi-Objective Optimization

Recommenders solve a constrained problem: **minimize** environmental impact (GHG, water
footprint) while **maximizing** user relevance and respecting financial + preference
constraints.

Architectural patterns:

- **Retail baskets:** evolutionary algorithms (NSGA-II) generate non-dominated
  recommendations that reduce total basket emissions while honoring consumer values.
- **E-commerce:** post-hoc reranking that linearly combines predicted user rating with
  a normalized carbon-footprint score.
- **Smart home / edge:** multi-agent architectures over IoT sensor data, extracting
  micro-moment features to produce explainable device-scheduling advice
  (~12% emission savings, ~7% cost reduction reported).
- **Forecasting:** **LSTM** networks model sequential history to forecast emissions; a
  **Genetic Algorithm** then optimizes allocation/transport/energy choices against
  multi-objective goals.

### The Green-AI Constraint

Deep-learning models carry a large training footprint — DL recommender experiments can
emit on the order of thousands of kg CO₂e, and identical experiments vary up to ~12×
by data-center grid. Carbonizer must not become part of the problem.

**Green-AI commitments:**

- Prefer **reduced space/time complexity** architectures. Where sequence modeling is
  needed, favor linear-complexity designs such as **RWKV** (residual blocks + LoRA),
  reducing time complexity O(n²) → O(n) and space O(n² + n) → O(1).
- **Edge-first deployment.** Constant-memory models run on consumer devices rather than
  leaning on centralized cloud inference, cutting operational carbon.
- Track and report the system's own footprint as a first-class metric.

---

## 8. Behavioral Economics & Choice Architecture

Quantitative accuracy alone does not change behavior. The UI is grounded in dual-process
theory (Thaler & Sunstein): **System 1** (fast, automatic, heuristic) vs. **System 2**
(slow, analytical, effortful). Raw technical metrics tax System 2 → fatigue → abandonment.

### Nudge Toolkit

- **Defaults (most potent).** Exploit status-quo bias by making the **low-carbon option
  the default** (e.g., "no single-use cutlery" by default beats pop-up reminders).
- **Informational nudges.** High-frequency tailored feedback yields modest reductions
  (~0.7–15%).
- **Social nudges.** Peer benchmarking normalizes sustainable behavior; learning you're
  above the neighborhood average drives sustained reductions (~6.7–11%). Benchmarks must
  be contextual — compare against similar household size and income (CoolClimate model),
  not a vacuum.
- **Gamification.** Points, leaderboards, and variable rewards counter present bias.
  Favor **intrinsic** motivation (more stable over time) over purely extrinsic monetary
  rewards.
- **Tangible equivalents.** Translate abstract tonnage into vivid imagery (e.g.,
  "saved 17 trees") to boost emotional resonance.

### Framing Caution

Avoid over-emphasizing individual responsibility to the point of disengagement
(the "it's all on me" trap). Link individual tracking to **collective/corporate
transparency** so users feel part of a systemic effort, not isolated against it.

---

## 9. Systemic Layer — Decentralized Web3 & Personal Carbon Trading (Optional)

A forward-looking module extends tracking into **Personal Carbon Trading (PCT)**: a
per-citizen carbon allowance forming a micro cap-and-trade market. Legacy PCT failed on
administrative complexity, insecure accounting, high transaction costs, and opacity —
problems that DLT addresses.

| Mechanism | Function | Benefit |
|---|---|---|
| **Tokenization & Allocation** | Cryptographic tokens represent each user's allowance per compliance period | Seamless transfer/division of credits |
| **Oracle Integration** | Trusted off-chain sources (IoT, telematics SDK, smart meters) feed verified data on-chain | Bridges physical activity ↔ ledger |
| **Smart-Contract Automation** | Auto-deducts tokens per reported emissions; enforces penalties | Removes manual auditing/bias |
| **P2P Trading** | Prosumers sell surplus credits directly to peers | No intermediaries; lower cost |

Immutability prevents double-counting of offsets. Macro precedents: World Bank CATS and
the open-source Climate Action Data Trust (CAD Trust). Smart contracts modeled on
Hyperledger Fabric (cf. STRICTs) automate auditing without centralized escrow.

> This layer is **optional / future-phase** and must remain isolated from core tracking
> so the product is fully functional without it.

---

## 10. Privacy, Security & Regulatory Compliance

Aggregating financial history + high-frequency location + utility usage creates an
exceptionally sensitive data repository. Compliance with **GDPR** and India's **DPDP Act
2023** is foundational, not bolt-on.

### Consent

- Consent must be **free, specific, informed, and unambiguous**. Plain-language notices
  stating *what* is collected, *why*, and *with whom* it is shared — no burying terms in
  40-page T&Cs.
- **Purpose limitation:** data collected for carbon tracking may not be reused for
  advertising/profiling without separate explicit consent.
- Support **Consent Managers** (DPDP) for programmatic grant/review/withdraw.
- **Withdrawal must be as frictionless as opt-in** — symmetric click cost.

### Data Lifecycle & Rights

- **Retention limits & Right to Erasure.** Automatic erasure workflows after defined
  inactivity (e.g., one year), with a mandatory **48-hour advance notice**.
- **Native data degradation** (Tracelet-style): coordinates snappable to coarse 1 km
  grids, or processed **event-only** in isolated device memory — never written to disk or
  synced.

### Security Safeguards

- Strict access controls, continuous logging (1-year retention), verified backups.
- Encryption / masking / tokenization of personal data **at rest and in transit**.
- **Breach reporting** to the Data Protection Board of India (and affected users) within
  **72 hours**. Non-compliance penalties extend up to ₹200 crore.
- Deploy **Data Security Posture Management (DSPM)** to automate data discovery,
  risk-based classification, and dynamic access control for audit-ready compliance.

### Privacy-by-Design Defaults

- Minimize collection; prefer on-device processing.
- Default location precision to the coarsest level that still serves the feature.
- Keep the optional Web3 layer cryptographically partitioned from PII.

---

## 11. Component Summary

| Layer | Component | Primary Technology / Standard |
|---|---|---|
| Accounting | CO₂e engine | IPCC, GHG Protocol, DEFRA, GWP-100 |
| Ingestion | Financial | Open Banking / PSD2, MCC, Climatiq, RoBERTa classifier |
| Ingestion | Mobility | Rust core + UniFFI, CoreMotion / Activity Recognition, Extended Kalman Filter |
| Ingestion | Energy | DCC / MAM, Octopus REST API, grid carbon intensity |
| Intelligence | Recommender | NSGA-II, post-hoc reranking, LSTM + GA, RWKV (Green AI) |
| Behavior | Nudge layer | Defaults, social benchmarking, gamification, equivalents |
| Settlement | PCT (optional) | Hyperledger Fabric, smart contracts, oracles, P2P tokens |
| Compliance | Privacy/Security | GDPR, DPDP Act 2023, DSPM, encryption/tokenization |

---

## 12. Open Questions & Future Work

- **Activity ↔ spend reconciliation:** how to avoid double-counting when a transaction
  and a telematics/utility signal describe the same activity.
- **Classifier maintenance:** retraining cadence and drift monitoring for the NLP
  transaction model.
- **Regional emission-factor coverage:** prioritization of localized factor databases
  beyond UK/EU.
- **Green-AI accounting:** methodology for measuring and publishing Carbonizer's own
  operational footprint.
- **PCT viability:** regulatory and UX prerequisites before promoting the Web3 layer out
  of optional/experimental status.

---

*This document synthesizes the product research into an architectural blueprint. It is a
living design artifact and should be revised as implementation decisions are made.*
