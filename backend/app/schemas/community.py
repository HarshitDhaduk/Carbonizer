"""Community schemas — mirror the frontend Benchmark type."""

from __future__ import annotations

from app.schemas.common import CamelModel


class Benchmark(CamelModel):
    """R4 cohort comparison — IPW-corrected, DP-noised, k-anonymity-gated."""

    you_tco2e: float
    average_tco2e: float
    top_tco2e: float
    vs_average_pct: float
    # suppressed (None) below the k-anonymity threshold
    cohort_size: int | None = None
    # R4: average is selection-bias-corrected (IPW) + differentially-private
    privacy_adjusted: bool = False
