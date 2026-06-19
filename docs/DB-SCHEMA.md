# Carbonizer — Database Schema (PostgreSQL 16)

Normalized schema for the FastAPI backend. Implements the accounting model
(docs/DESIGN.md §2), the API contract (docs/API-DESIGN.md), and the privacy regime
(docs/DESIGN.md §10). SQLAlchemy 2.0 models live in
[`backend/app/models/`](../backend/app/models); Alembic owns migrations.

> Engine choices: **PostgreSQL** for JSONB, declarative range **partitioning** on
> high-volume time-series, generated columns, and row-level security. UUID v7 PKs
> (time-sortable, index-friendly). `numeric` for money/factors (no float drift);
> `double precision` only for derived `co2e_kg`.

---

## 1. Entity overview

```
users ──┬── connections ──< raw_transactions ┐
        │                ──< raw_trips        ├──> ledger_entries >── emission_factors
        │                ──< raw_energy_reads ┘         │
        │                                                └──(agg)──> category_rollups ──> footprint_snapshots
        ├── consents              recommendations ──< recommendation_actions
        ├── privacy_settings      user_cohort >── cohorts
        ├── erasure_jobs          challenge_participants >── challenges
        └── sessions / audit_log / idempotency_keys
```

Two-layer accounting: **raw_* tables** hold provider data verbatim (auditable,
re-computable); **ledger_entries** is the single normalized CO₂e stream every
rollup and snapshot derives from. Recomputing factors never mutates raw data.

---

## 2. Enumerated types

```sql
CREATE TYPE category        AS ENUM ('transport','energy','food','spend','home');
CREATE TYPE calc_method     AS ENUM ('activity','spend','estimated');
CREATE TYPE source_type     AS ENUM ('transaction','trip','energy');
CREATE TYPE provider_kind   AS ENUM ('bank','telematics','meter');
CREATE TYPE conn_status     AS ENUM ('disconnected','connecting','connected','needs_attention');
CREATE TYPE trip_mode       AS ENUM ('car','bus','train','cycle','walk','flight','other');
CREATE TYPE biome_status    AS ENUM ('seed','regressing','plateau','improving','thriving');
CREATE TYPE nudge_kind      AS ENUM ('action','default-swap','clean-window');
CREATE TYPE nudge_effort    AS ENUM ('1-tap','5-min','setup');
CREATE TYPE nudge_status    AS ENUM ('active','acted','dismissed','expired');
CREATE TYPE loc_precision   AS ENUM ('precise','coarse_1km','event_only');
CREATE TYPE dsr_kind        AS ENUM ('export','erase');     -- data-subject request
CREATE TYPE job_status      AS ENUM ('pending','running','completed','failed');
```

---

## 3. Core identity & privacy

### `users`
| column | type | notes |
|---|---|---|
| `id` | `uuid` PK | UUID v7 |
| `email` | `citext` UNIQUE NOT NULL | case-insensitive |
| `password_hash` | `text` NOT NULL | Argon2id |
| `region` | `text` NOT NULL | UN/LOCODE; default emission region |
| `household_size` | `smallint` | for cohorting |
| `income_band` | `text` | bucketed, never raw income |
| `target_tco2e` | `numeric(6,2)` | personalized annual target |
| `created_at` | `timestamptz` NOT NULL DEFAULT now() | |
| `deleted_at` | `timestamptz` | soft-delete; hard purge via erasure job |

`CREATE UNIQUE INDEX ix_users_email ON users (email) WHERE deleted_at IS NULL;`

### `privacy_settings` (1:1 with user)
`user_id` PK FK · `location_precision loc_precision NOT NULL DEFAULT 'coarse_1km'`
· `retention_days int NOT NULL DEFAULT 365` · `marketing_opt_in bool DEFAULT false`
· `updated_at timestamptz`.

### `consents`
Granular, withdrawable record per purpose (DPDP Consent-Manager friendly).
`id` PK · `user_id` FK · `connection_id` FK NULL · `scope text` · `purpose text`
· `granted_at timestamptz` · `withdrawn_at timestamptz` · `consent_manager_ref text`.
> Purpose-limitation enforced in the service layer: a query for purpose X rejects
> data whose consent was granted only for purpose Y.

### `sessions` (refresh tokens)
`id` PK · `user_id` FK · `token_hash text` (sha256, never store raw) · `expires_at`
· `revoked_at` · `user_agent` · `created_at`.
`CREATE INDEX ix_sessions_user ON sessions (user_id) WHERE revoked_at IS NULL;`

---

## 4. Connections & raw ingestion

### `connections`
`id` PK · `user_id` FK · `provider provider_kind` · `status conn_status` ·
`external_account_ref text` · `access_token_enc bytea` (envelope-encrypted) ·
`last_sync_at` · `created_at`.
`UNIQUE (user_id, provider, external_account_ref)`.

### `emission_factors` (catalog — slowly changing)
| column | type | notes |
|---|---|---|
| `id` | `uuid` PK | |
| `source` | `text` | `defra` / `climatiq` / `eea_2024` / `ecoinvent` … |
| `category` | `category` | |
| `activity_key` | `text` | e.g. `road.car.petrol`, `mcc.5411`, `grid.gb` |
| `unit` | `text` | `km`, `kwh`, `gbp` |
| `factor` | `numeric(14,6)` | kgCO₂e per unit |
| `gwp_method` | `text` | `ipcc_ar6_gwp100` … |
| `region` | `text` | UN/LOCODE or country |
| `valid_from` / `valid_to` | `date` | temporal validity |

`CREATE INDEX ix_ef_lookup ON emission_factors (category, activity_key, region, valid_from DESC);`
A ledger entry pins the exact `factor_id` used → reproducible, auditable figures.

### High-volume raw tables — **range-partitioned by month**

All three are partitioned on their event timestamp; old partitions are detached and
dropped per the user's `retention_days` (cheap bulk erasure). Shared shape:
`id` · `user_id` FK · `connection_id` FK · `external_id text` · event time · payload
columns · `processed_at` (NULL until the engine emits a ledger entry).

```sql
CREATE TABLE raw_transactions (
  id              uuid NOT NULL,
  user_id         uuid NOT NULL,
  connection_id   uuid NOT NULL,
  external_id     text NOT NULL,
  booked_at       timestamptz NOT NULL,
  amount_minor    bigint NOT NULL,
  currency        char(3) NOT NULL,
  mcc             char(4),
  description      text,
  merchant        text,
  spend_region    text,
  commodity_class text,                 -- NLP/MCC classification result
  processed_at    timestamptz,
  PRIMARY KEY (id, booked_at)
) PARTITION BY RANGE (booked_at);

-- idempotent ingest: provider id is unique per user
CREATE UNIQUE INDEX ux_txn_ext ON raw_transactions (user_id, external_id, booked_at);
CREATE INDEX ix_txn_unprocessed ON raw_transactions (processed_at) WHERE processed_at IS NULL;
```

`raw_trips` (`started_at`, `mode trip_mode`, `distance_m int`, `region`) and
`raw_energy_reads` (`interval_start`, `kwh numeric(10,3)`, `fuel text`,
`grid_intensity numeric(7,2)`) follow the same partitioning + unique-external-id
pattern.

---

## 5. Emissions ledger & rollups

### `ledger_entries` — **range-partitioned by month** on `occurred_at`
The normalized CO₂e stream. One row per computed emission.

| column | type | notes |
|---|---|---|
| `id` | `uuid` | PK `(id, occurred_at)` |
| `user_id` | `uuid` FK | |
| `category` | `category` | |
| `source_type` | `source_type` | which raw table |
| `source_id` | `uuid` | FK-by-convention into raw_* (cross-partition) |
| `method` | `calc_method` | activity / spend / estimated |
| `co2e_kg` | `double precision` NOT NULL | |
| `factor_id` | `uuid` FK | exact factor used |
| `occurred_at` | `timestamptz` NOT NULL | event time |
| `created_at` | `timestamptz` DEFAULT now() | compute time |

```sql
CREATE INDEX ix_ledger_user_time ON ledger_entries (user_id, occurred_at DESC);
CREATE INDEX ix_ledger_user_cat  ON ledger_entries (user_id, category, occurred_at DESC);
```

### `category_rollups` — pre-aggregated buckets (refreshed incrementally)
`user_id` · `category` · `bucket_start date` · `granularity text(week|month)` ·
`co2e_kg double precision` · `method_mix jsonb` · `updated_at`.
PK `(user_id, category, granularity, bucket_start)`. Powers `/footprint/timeseries`
and the sparklines without scanning the ledger.

> Implementation: incremental refresh on ledger insert (trigger or async worker).
> A `MATERIALIZED VIEW` is the simpler v1; switch to a maintained table when write
> volume warrants. Sub-100ms dashboard reads come from here + `footprint_snapshots`.

### `footprint_snapshots` — `/footprint/summary` cache
`id` · `user_id` · `range text` · `total_tco2e numeric` · `delta_pct numeric` ·
`status biome_status` · `health numeric(4,3)` · `target_tco2e numeric` ·
`payload jsonb` (full response) · `generated_at`. Unique `(user_id, range)`.

---

## 6. Recommendations

### `recommendations`
`id` PK · `user_id` FK · `kind nudge_kind` · `title` · `detail` ·
`carbon_saved_tco2e numeric(8,4)` · `money_saved_minor bigint` · `currency char(3)` ·
`effort nudge_effort` · `window_ends_at timestamptz NULL` · `score real` ·
`status nudge_status DEFAULT 'active'` · `created_at`.
`CREATE INDEX ix_rec_active ON recommendations (user_id, score DESC) WHERE status='active';`

### `recommendation_actions`
`id` · `recommendation_id` FK · `user_id` FK · `action text('acted'|'dismissed')` ·
`realized_saving_tco2e numeric` · `acted_at`. Feeds the ranker; one acted row caps
via app-level idempotency.

---

## 7. Community (k-anonymized)

### `cohorts`
`id` PK · `household_size_band text` · `income_band text` · `region text` ·
`size int` · `avg_tco2e numeric` · `top_tco2e numeric` (20th pct) · `updated_at`.
`UNIQUE (household_size_band, income_band, region)`.

### `user_cohort`  `user_id` PK FK · `cohort_id` FK.
Benchmark endpoint returns cohort aggregates only, and suppresses `cohort_size`
when `size < 50` (k-anonymity).

### `challenges` / `challenge_participants`
`challenges`: `id` · `slug` UNIQUE · `title` · `description` · `starts_at` ·
`ends_at` · `target_metric jsonb`.
`challenge_participants`: PK `(challenge_id, user_id)` · `joined_at` · `progress numeric`.

---

## 8. Privacy operations & audit

### `dsr_jobs` (data-subject requests: export / erase)
`id` PK · `user_id` FK · `kind dsr_kind` · `status job_status` · `requested_at` ·
`scheduled_purge_at timestamptz` (48-h grace, docs §10) · `completed_at` ·
`download_url text` · `error text`.

### `audit_log` — **range-partitioned by month**, 1-year retention
`id` · `actor_user_id uuid NULL` · `action text` · `resource_type text` ·
`resource_id text` · `ip inet` · `request_id text` · `created_at timestamptz`.
`CREATE INDEX ix_audit_actor_time ON audit_log (actor_user_id, created_at DESC);`
Append-only; written for every consent change, export, erase, and admin read.

### `idempotency_keys`
`key text` · `user_id uuid` · `endpoint text` · `response_hash text` ·
`created_at timestamptz`. PK `(user_id, key)`; TTL-swept after 24 h.

---

## 9. Retention, erasure & security

- **Retention:** a nightly job detaches/drops `raw_*` partitions older than each
  user's `retention_days`, after a 48-h advance notice (docs §10). Partitioning makes
  this an `O(1)` metadata op, not a mass `DELETE`.
- **Right to erasure:** `dsr_jobs(kind='erase')` → grace window → purge raw_* +
  ledger + connections + tokens for the user, tombstone `users.deleted_at`, and write
  a final `audit_log` entry. Cohort aggregates are unaffected (already anonymized).
- **Row-level security:** `ALTER TABLE … ENABLE ROW LEVEL SECURITY` with a
  `user_id = current_setting('app.user_id')::uuid` policy on all per-user tables;
  the request scope sets `app.user_id` per transaction — defense in depth behind the
  service layer.
- **Encryption:** `connections.access_token_enc` envelope-encrypted (KMS data key);
  TLS in transit; column-level for any residual PII. Passwords Argon2id.
- **Indexes target < 100ms:** dashboard reads hit `footprint_snapshots` /
  `category_rollups`; ledger drill-downs use `(user_id, category, occurred_at DESC)`;
  ingestion dedup uses the unique `(user_id, external_id, time)` partial indexes.

---

## 10. Partition & maintenance automation

- Use **`pg_partman`** (or a scheduled function) to pre-create next-month partitions
  for `raw_transactions`, `raw_trips`, `raw_energy_reads`, `ledger_entries`,
  `audit_log`, and to retain/detach per policy.
- `ANALYZE` partitions after bulk ingest; autovacuum tuned for append-heavy tables.
- Read replicas serve `/footprint/summary` and `/community/benchmark` (cacheable,
  `private, max-age=60`); writes/ingestion go to primary.

*Migrations are additive-first; destructive changes ship behind expand/contract.*
