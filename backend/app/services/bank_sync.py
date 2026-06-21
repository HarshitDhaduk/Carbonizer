"""Ingestion + footprint recompute (docs/DATA-STRATEGY.md §3-4).

`sync_bank` / `sync_meter` pull from the providers and persist idempotently.
`recompute_footprint` merges the available signals over the onboarding estimate,
honoring the data-quality hierarchy **activity > spend > estimated** per category:

  • energy  → metered kWh × grid intensity (activity) if a meter is connected,
              else utility spend (spend), else the estimate.
  • food / transport / spend → transaction spend (merchant-aware, R2) if present,
              else the estimate.

Each upgrade flips that category's `method`, growing the measured share of the
footprint (Progressive Data Depth).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emission import FootprintSnapshot
from app.models.enums import CalcMethod, Category, Trend
from app.models.ingestion import RawEnergyRead, RawTransaction
from app.schemas.footprint import CategoryBreakdown, FootprintSummary
from app.services import carbon, estimator, impute
from app.services.providers import (
    WINDOW_DAYS,
    get_bank_provider,
    get_meter_provider,
)

_DISPLAY = [Category.transport, Category.energy, Category.food, Category.spend]
_ANNUALIZE = 365 / WINDOW_DAYS


async def sync_bank(
    db: AsyncSession, user_id: uuid.UUID, connection_id: uuid.UUID
) -> int:
    """Fetch + upsert bank transactions. Returns rows fetched."""
    provider = get_bank_provider("sandbox")
    txns = await provider.fetch_transactions(user_id, datetime.now(UTC))
    if not txns:
        return 0
    rows = [
        {
            "id": uuid.uuid4(),
            "booked_at": t.booked_at,
            "user_id": user_id,
            "connection_id": connection_id,
            "external_id": t.external_id,
            "amount_minor": t.amount_minor,
            "currency": t.currency,
            "mcc": t.mcc,
            "description": t.description,
            "merchant": t.merchant,
            "spend_region": "GB",
        }
        for t in txns
    ]
    stmt = pg_insert(RawTransaction).values(rows).on_conflict_do_nothing(
        index_elements=["user_id", "external_id", "booked_at"]
    )
    await db.execute(stmt)
    return len(txns)


async def sync_meter(
    db: AsyncSession, user_id: uuid.UUID, connection_id: uuid.UUID
) -> int:
    """Fetch + upsert smart-meter energy reads. Returns rows fetched."""
    provider = get_meter_provider("sandbox")
    reads = await provider.fetch_energy(user_id, datetime.now(UTC))
    if not reads:
        return 0
    rows = [
        {
            "id": uuid.uuid4(),
            "interval_start": r.interval_start,
            "user_id": user_id,
            "connection_id": connection_id,
            "external_id": r.external_id,
            "kwh": r.kwh,
            "fuel": r.fuel,
            "grid_intensity": r.grid_intensity_g,
        }
        for r in reads
    ]
    stmt = pg_insert(RawEnergyRead).values(rows).on_conflict_do_nothing(
        index_elements=["user_id", "external_id", "interval_start"]
    )
    await db.execute(stmt)
    return len(reads)


def _spark(old: float | None, new: float) -> list[float]:
    if old is None:
        return [round(new, 2)] * 6
    return [round(old + (new - old) * i / 5, 2) for i in range(6)]


def _delta(old: float | None, new: float) -> tuple[float, Trend]:
    if not old:
        return 0.0, Trend.flat
    pct = round((new - old) / old * 100, 1)
    trend = Trend.down if new < old else Trend.up if new > old else Trend.flat
    return pct, trend


def _breakdown(
    cat: Category, new_v: float, method: CalcMethod,
    prior: dict[Category, CategoryBreakdown],
    *,
    confidence: float | None = None,
    imputed: bool = False,
) -> CategoryBreakdown:
    old_v = float(prior[cat].tco2e) if cat in prior else None
    delta_pct, trend = _delta(old_v, new_v)
    conf = confidence if confidence is not None else impute.CONFIDENCE.get(method, 0.5)
    return CategoryBreakdown(
        category=cat, tco2e=round(new_v, 2), delta_pct=delta_pct, trend=trend,
        method=method, spark=_spark(old_v, round(new_v, 2)),
        confidence=conf, imputed=imputed,
    )


async def _collect_spend(
    db: AsyncSession, user_id: uuid.UUID, since: datetime
) -> tuple[dict[Category, float], float]:
    """Sum spend-based tCO2e per category + GBP turnover over the window.

    Returns ``(spend_tco2e, total_spend_gbp)``. Merchant-aware (R2): the
    carbon factor varies by merchant within an MCC.
    """
    tx_res = await db.execute(
        select(RawTransaction).where(
            RawTransaction.user_id == user_id, RawTransaction.booked_at >= since
        )
    )
    spend_tco2e: dict[Category, float] = {}
    total_spend_gbp = 0.0
    for txn in tx_res.scalars().all():
        gbp = txn.amount_minor / 100
        total_spend_gbp += gbp
        cat = carbon.categorize(txn.mcc)
        kg = carbon.co2e_kg(cat, gbp, txn.merchant) * _ANNUALIZE
        spend_tco2e[cat] = spend_tco2e.get(cat, 0.0) + kg / 1000
    return spend_tco2e, total_spend_gbp


async def _collect_energy(
    db: AsyncSession, user_id: uuid.UUID, since: datetime
) -> float | None:
    """Activity-based annual energy tCO2e from metered reads, or None if no meter."""
    en_res = await db.execute(
        select(RawEnergyRead).where(
            RawEnergyRead.user_id == user_id,
            RawEnergyRead.interval_start >= since,
        )
    )
    energy_kg = 0.0
    has_energy = False
    for r in en_res.scalars().all():
        has_energy = True
        gi = float(r.grid_intensity) if r.grid_intensity is not None else None
        energy_kg += carbon.energy_co2e_kg(float(r.kwh), r.fuel, gi)
    return (energy_kg / 1000 * _ANNUALIZE) if has_energy else None


def _merge_categories(
    *,
    spend_tco2e: dict[Category, float],
    energy_activity: float | None,
    prior: dict[Category, CategoryBreakdown],
    bank_connected: bool,
    monthly_spend_gbp: float,
) -> list[CategoryBreakdown]:
    """Apply the data-quality hierarchy activity > spend > imputed > estimated.

    For each display category, pick the highest-quality signal we have. R1
    fires when the bank is connected but a category has no direct transactions
    — we impute from the hub signal rather than fall back to the flat estimate.
    """
    categories: list[CategoryBreakdown] = []
    for cat in _DISPLAY:
        if cat is Category.energy and energy_activity is not None:
            categories.append(
                _breakdown(cat, energy_activity, CalcMethod.activity, prior)
            )
        elif cat in spend_tco2e:
            categories.append(
                _breakdown(cat, spend_tco2e[cat], CalcMethod.spend, prior)
            )
        elif cat in prior and bank_connected:
            imp_v, conf = impute.impute_from_bank(
                float(prior[cat].tco2e), monthly_spend_gbp
            )
            categories.append(
                _breakdown(
                    cat, imp_v, CalcMethod.estimated, prior,
                    confidence=conf, imputed=True,
                )
            )
        elif cat in prior:
            categories.append(prior[cat])
        else:
            categories.append(
                CategoryBreakdown(
                    category=cat, tco2e=0.0, delta_pct=0.0, trend=Trend.flat,
                    method=CalcMethod.estimated, spark=[0.0] * 6,
                    confidence=impute.CONFIDENCE[CalcMethod.estimated],
                )
            )
    return categories


async def recompute_footprint(
    db: AsyncSession, user_id: uuid.UUID
) -> FootprintSummary:
    """Merge measured signals over the prior estimate and persist the snapshot."""
    now = datetime.now(UTC)
    since = now - timedelta(days=WINDOW_DAYS + 1)

    spend_tco2e, total_spend_gbp = await _collect_spend(db, user_id, since)
    bank_connected = total_spend_gbp > 0
    monthly_spend_gbp = total_spend_gbp * 30 / WINDOW_DAYS

    energy_activity = await _collect_energy(db, user_id, since)

    # prior snapshot (the estimate) to merge against
    snap_res = await db.execute(
        select(FootprintSnapshot).where(
            FootprintSnapshot.user_id == user_id, FootprintSnapshot.range == "12w"
        )
    )
    snapshot = snap_res.scalar_one_or_none()
    prior: dict[Category, CategoryBreakdown] = {}
    prior_total: float | None = None
    if snapshot is not None and snapshot.payload:
        prior_summary = FootprintSummary.model_validate(snapshot.payload)
        prior = {c.category: c for c in prior_summary.categories}
        prior_total = float(prior_summary.total_tco2e)

    categories = _merge_categories(
        spend_tco2e=spend_tco2e,
        energy_activity=energy_activity,
        prior=prior,
        bank_connected=bank_connected,
        monthly_spend_gbp=monthly_spend_gbp,
    )

    total = round(sum(c.tco2e for c in categories), 2)
    health = estimator.health_for_total(total)
    total_delta, total_trend = _delta(prior_total, total)
    summary = FootprintSummary(
        total_tco2e=total,
        delta_pct=total_delta,
        trend=total_trend,
        status=estimator.status_for_health(health),
        target_tco2e=round(max(2.0, total * 0.75), 1),
        health=round(health, 3),
        categories=categories,
        range="12w",
        generated_at=now,
    )

    if snapshot is None:
        snapshot = FootprintSnapshot(user_id=user_id, range="12w")
        db.add(snapshot)
    snapshot.total_tco2e = summary.total_tco2e
    snapshot.delta_pct = summary.delta_pct
    snapshot.status = summary.status
    snapshot.health = summary.health
    snapshot.target_tco2e = summary.target_tco2e
    snapshot.payload = summary.model_dump(mode="json")
    snapshot.generated_at = now
    return summary
