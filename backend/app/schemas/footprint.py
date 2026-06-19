"""Footprint schemas — mirror the frontend FootprintSummary type exactly."""

from __future__ import annotations

from datetime import datetime

from app.models.enums import BiomeStatus, CalcMethod, Category, Trend
from app.schemas.common import CamelModel


class CategoryBreakdown(CamelModel):
    category: Category
    tco2e: float
    delta_pct: float
    trend: Trend
    method: CalcMethod
    spark: list[float]
    # R1: calibrated confidence 0..1 (activity ≈ 0.95 → estimated ≈ 0.3). Optional
    # so snapshots written before R1 still validate.
    confidence: float = 1.0
    # R1: true when a category was imputed from the bank "hub" rather than measured.
    imputed: bool = False


class Attribution(CamelModel):
    """R3 — energy ΔCO₂e split into behavioral (usage) vs structural (grid)."""

    available: bool
    period_days: int = 0
    total_delta_kg: float = 0.0
    behavioral_kg: float = 0.0
    structural_kg: float = 0.0
    behavior_share: float = 0.0  # |behavioral| / (|behavioral| + |structural|)


class FootprintSummary(CamelModel):
    total_tco2e: float
    delta_pct: float
    trend: Trend
    status: BiomeStatus
    target_tco2e: float
    health: float
    categories: list[CategoryBreakdown]
    # extra context (TS client ignores unknown fields)
    range: str = "12w"
    generated_at: datetime | None = None
