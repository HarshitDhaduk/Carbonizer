# Architecture Decision Records

This folder holds short, dated records of the load-bearing architectural
decisions in Carbonizer. Each ADR follows the same shape — Status, Context,
Decision, Consequences — so a reviewer can skim the *why* without rereading
the whole codebase.

ADRs are append-only: a decision that gets reversed becomes a new ADR
(`Status: superseded by ADR-NNNN`) rather than an edit. Numbers are zero-
padded, monotonic, and never re-used.

## Template

```markdown
# ADR-NNNN — Short imperative title

**Status:** Accepted | Proposed | Superseded by ADR-MMMM
**Date:** YYYY-MM-DD

## Context
Why this came up. What we were trying to solve, what we considered, the
constraints that shaped the call.

## Decision
The actual choice, in one sentence at the top, then a short paragraph on
how it works.

## Consequences
What follows — positive, negative, and "future us will need to think
about this when X happens."
```

## Index

* [ADR-0001 — Server-defined questionnaire](0001-server-defined-questionnaire.md)
* [ADR-0002 — Heuristics with an ML seam](0002-heuristics-with-ml-seam.md)
* [ADR-0003 — JWT in HttpOnly cookies, not localStorage](0003-jwt-in-cookies.md)
* [ADR-0004 — Partition `raw_*` tables](0004-partition-raw-tables.md)
* [ADR-0005 — Sandbox provider has no utility transactions](0005-sandbox-no-utility-spend.md)
