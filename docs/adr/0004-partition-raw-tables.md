# ADR-0004 — Partition the `raw_*` tables by month

**Status:** Accepted
**Date:** 2026-04-22

## Context

The raw-data tables (`raw_transactions`, `raw_trips`, `raw_energy_reads`,
plus `ledger_entries` and `audit_log`) grow with **every** ingestion sync.
A typical connected user with one bank + one meter generates on the order
of 30 transactions/week + 336 half-hourly meter reads/week. At 10k users
that's ~2M rows/week per table — fine for a year, painful for five.

Three concerns drove the choice:

1. **Retention.** GDPR / DPDP push toward "delete what you no longer need."
   A user disconnecting a source means we should drop their raw data with
   bounded latency. Without partitions, that's a giant `DELETE` that
   shreds the index and bloats the heap.
2. **Scan bounds.** The dashboard's recompute reads the *last 12 weeks*
   of transactions for each user. Without partitions, the query needs an
   index lookup over the entire table — fine while it's hot, painful
   once the dataset doesn't fit RAM.
3. **Audit isolation.** The `audit_log` table holds a year of security
   events. We don't want auth events from 13 months ago slowing today's
   login query.

## Decision

The five high-volume tables are **declarative PARTITION BY RANGE**
(monthly) on the natural time column:

| Table | Partition key |
|---|---|
| `raw_transactions` | `booked_at` |
| `raw_trips` | `started_at` |
| `raw_energy_reads` | `interval_start` |
| `ledger_entries` | `period_start` |
| `audit_log` | `created_at` |

The migration `c3f1a2b4d5e6_default_partitions` creates a `*_default`
partition per table so inserts never fail because a month's child doesn't
exist yet; monthly children are created by an ops job (Phase 7 — runbook).

The autogenerate hook in
[`alembic/env.py`](../../backend/alembic/env.py) explicitly excludes
`*_default` from comparison so future `revision --autogenerate` runs
don't try to drop them.

## Consequences

* **Retention drop is `DROP TABLE`** (and `DETACH PARTITION` if we want
  to keep the data around for legal hold) instead of a transactional
  delete. ~milliseconds rather than seconds-to-minutes.
* **Scan bounds**: the planner can partition-prune to the relevant 3
  months when the recompute window is 12 weeks; rows outside the
  window are never read.
* **Audit retention** (1-year, per [security review](../SECURITY-REVIEW.md))
  is a `DROP TABLE` on the 13th-month-back partition.
* Cost: the FK from `raw_*.user_id → users.id` requires `ON DELETE
  CASCADE` to actually fire across partitions (which it does — Postgres
  handles this transparently in PG 12+). DSR erasure
  (`services/dsr.py._purge_user`) explicit-deletes per table anyway to
  remain provider-agnostic in case we ever migrate off Postgres.
* The `_default` partition is a hot footgun — if the monthly-child cron
  ever stops, inserts land there and become slow. Monitor with
  `pg_stat_user_tables` and alert on default-partition row count rising.
