# Carbonizer — API Design

REST API contract for the FastAPI backend. Implemented with FastAPI + Pydantic v2,
served under a versioned prefix and consumed by the Next.js frontend
([`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts)).

> Design principles: resource-oriented, predictable, privacy-first. Every endpoint
> that returns an emission figure also returns **how it was derived** (activity vs.
> spend) so the client never hides data quality (docs/DESIGN.md §2).

---

## 1. Conventions

| Concern | Decision |
|---|---|
| Base path | `/api/v1` (URI versioning; breaking changes → `/api/v2`) |
| Format | JSON only; `Content-Type: application/json`; UTF-8 |
| Casing | **`camelCase`** keys on the wire (matches the existing TS client types). Python models stay `snake_case` and serialize via a Pydantic alias generator. *(Example payloads below use snake_case for readability; the implementation emits camelCase — e.g. `total_tco2e` → `totalTco2e`.)* |
| Auth | OAuth2 password grant → short-lived **JWT access** (15 min) + rotating **refresh** (30 d) cookie |
| Time | ISO-8601 UTC (`2026-06-17T16:00:00Z`) |
| IDs | UUID v7 (time-sortable) as strings, prefixed per resource (`txn_…`, `conn_…`) |
| Money | minor-unit integer + ISO-4217 `currency` (avoid float drift) |
| Carbon | `co2e_kg` as float; the client formats t/kg |
| Errors | RFC 9457 `application/problem+json` |
| Pagination | cursor-based (`?cursor=&limit=`), `limit` ≤ 100 |
| Idempotency | `Idempotency-Key` header on all unsafe POSTs (ingestion, actions) |
| Rate limits | per-user token bucket; `RateLimit-*` headers; `429` on exceed |
| Tracing | `X-Request-Id` echoed on every response |

### Standard error shape (RFC 9457)

```json
{
  "type": "https://api.carbonizer.app/errors/validation",
  "title": "Validation failed",
  "status": 422,
  "detail": "spend_region must be a valid UN/LOCODE",
  "instance": "/api/v1/ingest/transactions",
  "errors": [{ "field": "spend_region", "code": "invalid_format" }],
  "request_id": "req_01J..."
}
```

**Error catalog (selected):** `400 invalid_request` · `401 unauthenticated` ·
`403 consent_required` / `forbidden` · `404 not_found` · `409 conflict` /
`idempotency_replay` · `422 validation` · `429 rate_limited` · `503 provider_unavailable`.

---

## 2. Resource map

```
/api/v1
├── /auth            register · login · refresh · logout · me
├── /connections     list · link · callback · sync · disconnect      (data sources)
├── /ingest          transactions · trips · energy   (provider webhooks / edge oracle)
├── /footprint       summary · categories · timeseries · activities  (the ledger)
├── /recommendations list · act · dismiss                            (nudges)
├── /community       benchmark · challenges · join                   (social)
└── /privacy         consents · settings · export · erase            (GDPR / DPDP)
```

---

## 3. Auth

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/auth/register` | Create account `{email, password, region}` → `201` user + tokens |
| `POST` | `/auth/login` | OAuth2 password grant → access token (body) + refresh (HttpOnly cookie) |
| `POST` | `/auth/refresh` | Rotate refresh cookie → new access token |
| `POST` | `/auth/logout` | Revoke refresh token |
| `GET`  | `/auth/me` | Current user profile + targets |

`AccessToken` = `{ access_token, token_type: "bearer", expires_in }`. All other
endpoints require `Authorization: Bearer <access_token>`.

---

## 4. Connections & Ingestion

The user authorizes data sources; providers push data which the engine converts to
CO₂e. Connections never block the dashboard — it degrades to spend-based estimates.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/connections` | List connections + status (`disconnected\|connecting\|connected\|needs-attention`) |
| `POST` | `/connections/{provider}/link` | Begin OAuth/consent flow → `{ authorize_url, state }`. `provider ∈ {bank, telematics, meter}` |
| `GET` | `/connections/{provider}/callback` | Provider redirect; exchanges code, stores consent → `302` to app |
| `POST` | `/connections/{id}/sync` | Force a re-pull (idempotent); `202 Accepted` |
| `DELETE` | `/connections/{id}` | Revoke + purge derived data for that source |

### Ingestion (machine-to-machine: provider webhooks / edge oracle)

Authenticated by HMAC signature header (`X-Signature`), not user JWT. Idempotent by
`external_id`.

| Method | Path | Body |
|---|---|---|
| `POST` | `/ingest/transactions` | Open Banking transactions `[{external_id, booked_at, amount_minor, currency, mcc, description, merchant, spend_region}]` |
| `POST` | `/ingest/trips` | Telematics trips `[{external_id, started_at, ended_at, mode, distance_m, region}]` |
| `POST` | `/ingest/energy` | Half-hourly meter reads `[{external_id, interval_start, kwh, fuel, mpan_or_mprn}]` |

Each returns `{ accepted, duplicates, rejected[] }`. Classification + emission-factor
mapping happen asynchronously; results surface via `/footprint/*`.

---

## 5. Footprint (the ledger)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/footprint/summary` | **Primary dashboard call.** `?range=12w\|6m\|1y` |
| `GET` | `/footprint/categories/{category}` | Drill-down for one category + factor provenance |
| `GET` | `/footprint/timeseries` | `?metric=co2e&bucket=week&from=&to=` for charts |
| `GET` | `/footprint/activities` | Paginated activity ledger (each line item + method + factor source) |

### `GET /footprint/summary` → `200`

Mirrors the frontend `FootprintSummary` type exactly.

```json
{
  "range": "12w",
  "total_tco2e": 4.2,
  "delta_pct": -8,
  "trend": "down",
  "status": "improving",
  "target_tco2e": 3.5,
  "health": 0.62,
  "categories": [
    {
      "category": "transport",
      "tco2e": 1.1,
      "delta_pct": 4,
      "trend": "up",
      "method": "activity",
      "spark": [0.9, 1.0, 0.95, 1.05, 1.0, 1.1]
    }
  ],
  "generated_at": "2026-06-17T09:00:00Z"
}
```

`method ∈ {activity, spend, estimated}` · `trend ∈ {up, down, flat}` ·
`status ∈ {seed, regressing, plateau, improving, thriving}`.

---

## 6. Recommendations (nudges)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/recommendations` | Ranked nudges `?effort=&kind=` |
| `POST` | `/recommendations/{id}/act` | Mark acted; returns realized/queued saving (idempotent) |
| `POST` | `/recommendations/{id}/dismiss` | Suppress (feeds the ranker) |

### `Nudge` (matches frontend)

```json
{
  "id": "n-ev-offpeak",
  "kind": "clean-window",
  "title": "Clean-energy window until 4pm",
  "detail": "Shift your EV charge to now — the grid is running on renewables.",
  "carbon_saved_tco2e": 0.0018,
  "money_saved": 0.80,
  "currency": "GBP",
  "effort": "1-tap",
  "window_ends_at": "2026-06-17T16:00:00Z"
}
```

`kind ∈ {action, default-swap, clean-window}` · `effort ∈ {1-tap, 5-min, setup}`.
Clean-window savings are **per-event** (no `/yr`); others are annualized.

---

## 7. Community

Aggregates only — never another user's row-level data (docs/UI-UX-DESIGN.md §6.5).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/community/benchmark` | Cohort comparison (similar household size + income) |
| `GET` | `/community/challenges` | Joinable challenges |
| `POST` | `/community/challenges/{id}/join` | Join a challenge |

### `GET /community/benchmark` → `200`

```json
{
  "you_tco2e": 4.2,
  "average_tco2e": 4.6,
  "top_tco2e": 3.1,
  "vs_average_pct": -8,
  "cohort_size": 1840
}
```

`cohort_size` is suppressed (`null`) below a k-anonymity threshold (k=50).

---

## 8. Privacy & data rights (GDPR / DPDP)

Withdrawal must be as frictionless as opt-in (docs/DESIGN.md §10).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/privacy/consents` | List granted consents + scope + granted_at |
| `PATCH` | `/privacy/consents/{id}` | Narrow or withdraw a consent |
| `PATCH` | `/privacy/settings` | Location degradation (`precise\|coarse_1km\|event_only`), retention window |
| `POST` | `/privacy/export` | Request data export → `202` + async job; emailed download link |
| `POST` | `/privacy/erase` | Right to erasure → `202`; 48-h grace window then purge |

---

## 9. Cross-cutting

- **Caching:** `summary`/`benchmark` are `Cache-Control: private, max-age=60`; ledger is `no-store`.
- **HATEOAS-lite:** collection responses include `next_cursor`; resources include relevant action links where non-obvious.
- **Deprecation:** sunset via `Deprecation` + `Sunset` headers; min 6-month overlap.
- **OpenAPI:** FastAPI auto-generates `/api/v1/openapi.json` + Swagger UI at `/docs`, ReDoc at `/redoc`.
- **Health:** `GET /healthz` (liveness), `GET /readyz` (DB + provider reachability).

---

## 10. Onboarding (Day-0 estimate)

A short questionnaire produces an immediate `estimated` footprint so the dashboard/biome
are never empty (DATA-STRATEGY §4, "Progressive Data Depth"). The questionnaire is
**server-defined** so the estimation model and the UI never drift. `/profile` and
`/estimate` require auth; `/questions` is public (static form definition).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/onboarding/questions` | Questionnaire definition for the client to render |
| `GET` | `/onboarding/profile` | The current user's saved answers (`null` if not done) + `completed` flag |
| `POST` | `/onboarding/estimate` | Submit answers → compute + persist a snapshot → return the `FootprintSummary` |

### `GET /onboarding/questions` → `200`

Each question is self-describing; `type ∈ {single, number}`. The client renders from this
list; the server owns the option keys it will accept back.

```json
{
  "version": 1,
  "questions": [
    { "id": "householdSize", "type": "number", "label": "People in your household",
      "min": 1, "max": 12, "default": 2 },
    { "id": "homeType", "type": "single", "label": "Your home",
      "options": [
        { "value": "flat", "label": "Flat" },
        { "value": "terraced", "label": "Terraced" },
        { "value": "semi", "label": "Semi-detached" },
        { "value": "detached", "label": "Detached" }
      ], "default": "terraced" },
    { "id": "energySource", "type": "single", "label": "Home energy",
      "options": [
        { "value": "standard", "label": "Standard tariff" },
        { "value": "green", "label": "Green tariff" },
        { "value": "renewable", "label": "Mostly my own renewable" }
      ], "default": "standard" },
    { "id": "diet", "type": "single", "label": "Your diet",
      "options": [
        { "value": "meat_heavy", "label": "Meat with most meals" },
        { "value": "average", "label": "Average" },
        { "value": "low_meat", "label": "Low meat" },
        { "value": "vegetarian", "label": "Vegetarian" },
        { "value": "vegan", "label": "Vegan" }
      ], "default": "average" },
    { "id": "carType", "type": "single", "label": "Main car",
      "options": [
        { "value": "none", "label": "No car" },
        { "value": "petrol", "label": "Petrol" },
        { "value": "diesel", "label": "Diesel" },
        { "value": "hybrid", "label": "Hybrid" },
        { "value": "ev", "label": "Electric" }
      ], "default": "petrol" },
    { "id": "carKmPerWeek", "type": "number", "label": "Car km per week",
      "min": 0, "max": 2000, "default": 100, "unit": "km" },
    { "id": "shortFlightsPerYear", "type": "number", "label": "Short flights / year",
      "min": 0, "max": 50, "default": 1 },
    { "id": "longFlightsPerYear", "type": "number", "label": "Long-haul flights / year",
      "min": 0, "max": 30, "default": 0 }
  ]
}
```

### `POST /onboarding/estimate`

Request — a flat `answers` object keyed by question `id`. Unknown keys are ignored;
missing keys fall back to the question `default` (the estimate is intentionally
forgiving).

```json
{
  "answers": {
    "householdSize": 3, "homeType": "semi", "energySource": "standard",
    "diet": "average", "carType": "petrol", "carKmPerWeek": 120,
    "shortFlightsPerYear": 2, "longFlightsPerYear": 1
  }
}
```

Response → `200` with the same `FootprintSummary` shape as `GET /footprint/summary`
(every category `method: "estimated"`), so the client reuses dashboard rendering. The
answers are persisted to the user's profile and the result upserts the user's
`footprint_snapshots` row, so the dashboard immediately reflects it.

**Errors:** `401` unauthenticated · `422` validation (e.g. `carKmPerWeek` out of range) ·
`503` if `USE_DB=false` (estimate persistence requires the database).

---

*Contract owned jointly by frontend and backend. Changes that alter a response shape
require a version bump or additive-only evolution.*
