# ADR-0005 — Sandbox bank provider emits no utility transactions

**Status:** Accepted
**Date:** 2026-04-29

## Context

R1 (bank-as-hub imputation) only fires when **the bank is connected but
some category has no direct transactions** — that's the gap the
imputation is designed to fill. The clearest case is energy: a user
connects their bank but not a smart meter, and we need to infer their
energy emissions from their overall spending pattern rather than fall
back to the flat onboarding estimate.

If our sandbox bank provider includes a `MCC=4900` utility-bill
transaction every cycle (which is realistic — most people *do* pay their
energy supplier through their bank), the energy category gets a
spend-based reading from `_collect_spend` and the R1 imputation branch
never runs.

A developer or QA tester looking at a sandbox user would then **never see
the imputed-energy path** until they hand-edit the seed data, which
wastes review time and lets R1 regressions slip past.

## Decision

[`services/providers.SandboxBankProvider`](../../backend/app/services/providers.py)
deliberately omits utility-MCC transactions (`4900`, `4814`, `4815`,
`4816`) from its emitted set. Every other realistic MCC is represented —
groceries (`5411`), fuel (`5541`), dining, clothing, transport — so the
spend-derived categories (food, transport, spend) get coverage and the
recompute exercises the `> spend` branch of `_merge_categories`.

This forces the R1 imputation branch to fire on every sandbox bank
connection. Reviewers see the "Inferred" `MethodBadge` on the energy
card and confidence sits in the imputed band (between activity and
estimated) — exactly the behavior R1 is supposed to deliver.

## Consequences

* The sandbox is **deliberately unrealistic** in the same shape as a
  real user who pays utilities by direct debit from another account.
  That's a reasonable model; communicated via this ADR and a comment in
  `providers.py`.
* The R1 imputation path has live exercise on every connect — no
  regression can hide unless `test_bank_only_imputes_energy_via_R1`
  (testcontainers DB-mode) also breaks.
* The "real" GoCardless adapter (Phase 7) will include utility
  transactions when they're present in the user's data — the `_merge_
  categories` precedence handles both: spend wins over imputed when both
  are available.
* Tester awareness cost: a screen-shot of "sandbox bank + no meter
  shows imputed energy" might look like a bug to someone who hasn't
  read this ADR. The `MethodBadge` tooltip ("Inferred from your bank —
  connect more for a measured figure") covers most of that gap.
