# ADR-0002 — R0/R1/R2/R4 ship as heuristics with an ML seam

**Status:** Accepted
**Date:** 2026-04-12

## Context

The research-method (R) directions in
[`docs/DATA-STRATEGY.md`](../DATA-STRATEGY.md) — VoI ordering (R0),
bank-as-hub imputation (R1), price-elasticity (R2), IPW + Laplace DP
benchmarking (R4) — are framed in the literature as ML / inferential
problems. The "right" implementation of each one looks like:

* R0: a Bayesian posterior over user-level emission distributions, scored
  for expected information gain.
* R1: a graphical model linking transactions to imputed activity.
* R2: an econometric estimation of category-level price elasticities.
* R4: a debiased estimator with formal differential-privacy accounting.

All four are weeks-to-months of work each. At MVP scale (one-digit users,
no real telemetry pipeline yet) none of them are limiting accuracy — the
limiting factor is the **data sparsity** of a new user with zero
connections, and the right answer to that is "ship something defensible
today and replace the inside later".

## Decision

Each R direction ships as a **simple, transparent heuristic** today, with
its core math factored into a swappable function so an ML model can drop in
later without API or DB changes:

| R | Heuristic shipped today | Seam for ML drop-in |
|---|---|---|
| R0 | `_question_spread` measures the swing in total footprint as each question varies over its domain; normalised to 0..1 | `apply_voi(questions, estimate)` is a pure scoring function — swap for a Bayesian VoI estimator with the same signature |
| R1 | `impute.impute_from_bank(category_estimate, monthly_spend_gbp)` linearly nudges the category estimate by a regularised function of bank turnover; confidence is held at the imputed band | swap `impute_from_bank` for a per-user model; the recompute path keeps the same `(value, confidence)` tuple |
| R2 | `carbon.co2e_kg(category, gbp, merchant)` with merchant-aware priors (`MERCHANT_PRIORS`) and a per-category price elasticity coefficient | swap the merchant table for a learned merchant embedding; signature stays identical |
| R4 | `benchmark_stats.adjusted_average(connector_mean, sample_n)`: IPW lifts the eco-skewed connector population mean, Laplace noise is added with a fixed cohort seed | swap for a formal accountant + privacy-bookkept estimator; the call site doesn't care |

The heuristic implementations are exercised by `test_estimator_properties.py`
(Hypothesis property tests pin the invariants the ML replacements must also
preserve — non-negative categories, sum=total, health bounded, no-car
caps transport).

## Consequences

* **Today** the app works end-to-end and is defensible — every method has
  a known constant: how it can fail (R1 is too linear at high spend, R2's
  elasticity is the same per merchant within a category, etc.) is in the
  code comments.
* **Tomorrow** an ML replacement is one PR: replace the function body, run
  the property tests, ship. No API contract change, no DB migration, no
  client work.
* The property tests are the explicit invariant set the ML replacement
  must satisfy — if a learned R1 model produces negative imputed values
  for some answer combo, the test catches it before deploy.
* The confidence band (R1: `imputed`, R2: derived from sample size, R4:
  bumped down by k-anonymity threshold) is exposed in the API and the UI
  shows it (MethodBadge). When the ML replacement lands, the UI doesn't
  change — only the confidence trends up.
* Cost: a reader new to the codebase needs the table above to know "this
  is a heuristic, not the real thing"; that's why this ADR exists.
