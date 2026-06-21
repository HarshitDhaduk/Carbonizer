"""Footprint schemas — mirror the frontend FootprintSummary type exactly."""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict

from app.models.enums import BiomeStatus, CalcMethod, Category, Trend
from app.schemas.common import CamelModel, to_camel


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

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "totalTco2e": 4.2,
                    "deltaPct": -8.0,
                    "trend": "down",
                    "status": "improving",
                    "targetTco2e": 3.5,
                    "health": 0.72,
                    "categories": [
                        {
                            "category": "transport",
                            "tco2e": 1.6,
                            "deltaPct": -12.0,
                            "trend": "down",
                            "method": "spend",
                            "spark": [1.9, 1.85, 1.8, 1.75, 1.7, 1.6],
                            "confidence": 0.8,
                            "imputed": False,
                        }
                    ],
                    "range": "12w",
                    "generatedAt": "2026-06-21T08:30:00Z",
                }
            ],
        },
    )
