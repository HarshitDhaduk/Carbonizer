"""R3 — honest reduction attribution (docs/DATA-STRATEGY.md §9).

A drop in energy emissions can be the user using less (behavioral) *or* the grid
getting cleaner (structural) — only the first deserves credit. Using metered reads
with their time-of-use grid intensity, we split the window into a prior and a
current half and decompose ΔCO₂e exactly:

    behavioral = (kWh_curr − kWh_prior) · intensity_prior      (usage change @ old grid)
    structural = kWh_curr · (intensity_curr − intensity_prior) (grid change @ new usage)

which sum to the true Δ (kWh_c·i_c − kWh_p·i_p). Gas has no grid term, so its change
is wholly behavioral. This is the index-decomposition MVP; the full version adds
weather/price terms and per-user synthetic controls for nudge effects.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingestion import RawEnergyRead
from app.schemas.footprint import Attribution
from app.services.providers import WINDOW_DAYS

_GAS_FACTOR = 0.183  # kgCO2e/kWh (DEFRA)


def _elec_aggregate(reads: list[RawEnergyRead]) -> tuple[float, float]:
    """Return (total_kWh, kWh-weighted mean intensity gCO2/kWh) for electricity."""
    kwh = sum(float(r.kwh) for r in reads)
    if kwh <= 0:
        return 0.0, 0.0
    weighted = sum(
        float(r.kwh) * float(r.grid_intensity if r.grid_intensity is not None else 162)
        for r in reads
    )
    return kwh, weighted / kwh


async def energy_attribution(
    db: AsyncSession, user_id: uuid.UUID
) -> Attribution:
    """R3 — return the user's behaviour-vs-grid energy decomposition.

    Returns ``available=False`` when the meter doesn't have enough history to
    split the period in two; the dashboard then hides the attribution panel
    instead of presenting noise as signal.
    """
    now = datetime.now(UTC)
    since = now - timedelta(days=WINDOW_DAYS + 1)
    res = await db.execute(
        select(RawEnergyRead).where(
            RawEnergyRead.user_id == user_id,
            RawEnergyRead.interval_start >= since,
        )
    )
    reads = res.scalars().all()
    mid = now - timedelta(days=WINDOW_DAYS / 2)
    prior = [r for r in reads if r.interval_start < mid]
    curr = [r for r in reads if r.interval_start >= mid]
    if not prior or not curr:
        return Attribution(available=False)

    # electricity: decompose into usage vs grid
    pe = [r for r in prior if r.fuel == "electricity"]
    ce = [r for r in curr if r.fuel == "electricity"]
    kwh_p, int_p = _elec_aggregate(pe)
    kwh_c, int_c = _elec_aggregate(ce)
    behavioral_elec = (kwh_c - kwh_p) * int_p / 1000
    structural_elec = kwh_c * (int_c - int_p) / 1000

    # gas: fixed factor → entirely behavioral
    gas_p = sum(float(r.kwh) for r in prior if r.fuel == "gas")
    gas_c = sum(float(r.kwh) for r in curr if r.fuel == "gas")
    behavioral_gas = (gas_c - gas_p) * _GAS_FACTOR

    behavioral = behavioral_elec + behavioral_gas
    structural = structural_elec
    total = behavioral + structural
    denom = abs(behavioral) + abs(structural)
    share = abs(behavioral) / denom if denom > 0 else 0.0

    return Attribution(
        available=True,
        period_days=WINDOW_DAYS // 2,
        total_delta_kg=round(total, 2),
        behavioral_kg=round(behavioral, 2),
        structural_kg=round(structural, 2),
        behavior_share=round(share, 3),
    )
