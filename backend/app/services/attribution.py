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

_GAS_FACTOR_KG_PER_KWH = 0.183  # DEFRA
_DEFAULT_GRID_INTENSITY_G = 162  # gCO2/kWh — GB-wide mean (Carbon Intensity API, 2024)
_G_TO_KG = 1000


def _elec_aggregate(reads: list[RawEnergyRead]) -> tuple[float, float]:
    """Return (total_kWh, kWh-weighted mean intensity gCO2/kWh) for electricity."""
    kwh = sum(float(r.kwh) for r in reads)
    if kwh <= 0:
        return 0.0, 0.0
    weighted = sum(
        float(r.kwh)
        * float(
            r.grid_intensity
            if r.grid_intensity is not None
            else _DEFAULT_GRID_INTENSITY_G
        )
        for r in reads
    )
    return kwh, weighted / kwh


async def _fetch_reads(
    db: AsyncSession, user_id: uuid.UUID, since: datetime
) -> list[RawEnergyRead]:
    """Pull the user's energy reads in the window — caller splits by period."""
    res = await db.execute(
        select(RawEnergyRead).where(
            RawEnergyRead.user_id == user_id,
            RawEnergyRead.interval_start >= since,
        )
    )
    return list(res.scalars().all())


def _split_by_period(
    reads: list[RawEnergyRead], mid: datetime
) -> tuple[list[RawEnergyRead], list[RawEnergyRead]]:
    """Partition reads into (prior, current) halves around ``mid``."""
    prior = [r for r in reads if r.interval_start < mid]
    curr = [r for r in reads if r.interval_start >= mid]
    return prior, curr


def _decompose(
    prior: list[RawEnergyRead], curr: list[RawEnergyRead]
) -> tuple[float, float]:
    """Return (behavioral_kg, structural_kg) via index decomposition.

    Electricity splits into usage (behavioral) vs grid intensity (structural);
    gas has a fixed factor so its change is wholly behavioral.
    """
    pe = [r for r in prior if r.fuel == "electricity"]
    ce = [r for r in curr if r.fuel == "electricity"]
    kwh_p, int_p = _elec_aggregate(pe)
    kwh_c, int_c = _elec_aggregate(ce)
    behavioral_elec = (kwh_c - kwh_p) * int_p / _G_TO_KG
    structural_elec = kwh_c * (int_c - int_p) / _G_TO_KG

    gas_p = sum(float(r.kwh) for r in prior if r.fuel == "gas")
    gas_c = sum(float(r.kwh) for r in curr if r.fuel == "gas")
    behavioral_gas = (gas_c - gas_p) * _GAS_FACTOR_KG_PER_KWH

    return behavioral_elec + behavioral_gas, structural_elec


async def energy_attribution(
    db: AsyncSession, user_id: uuid.UUID
) -> Attribution:
    """R3 — return the user's behaviour-vs-grid energy decomposition.

    Returns ``available=False`` when the meter doesn't have enough history to
    split the period in two; the dashboard then hides the attribution panel
    instead of presenting noise as signal.
    """
    now = datetime.now(UTC)
    reads = await _fetch_reads(db, user_id, now - timedelta(days=WINDOW_DAYS + 1))
    prior, curr = _split_by_period(reads, now - timedelta(days=WINDOW_DAYS / 2))
    if not prior or not curr:
        return Attribution(available=False)

    behavioral, structural = _decompose(prior, curr)
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
