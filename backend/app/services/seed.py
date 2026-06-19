"""In-memory fixtures so the API runs without a database or real providers.

These mirror frontend/src/lib/mock-data.ts so the Next.js app gets identical data
whether it talks to this backend or its own mocks. When USE_DB=true, the services
read from Postgres instead.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.enums import (
    BiomeStatus,
    CalcMethod,
    Category,
    NudgeEffort,
    NudgeKind,
    Trend,
)
from app.schemas.community import Benchmark
from app.schemas.connection import DataConnection
from app.schemas.footprint import CategoryBreakdown, FootprintSummary
from app.schemas.recommendation import Nudge


def seed_summary() -> FootprintSummary:
    return FootprintSummary(
        total_tco2e=4.2,
        delta_pct=-8,
        trend=Trend.down,
        status=BiomeStatus.improving,
        target_tco2e=3.5,
        health=0.62,
        range="12w",
        generated_at=datetime.now(timezone.utc),
        categories=[
            CategoryBreakdown(
                category=Category.transport,
                tco2e=1.1,
                delta_pct=4,
                trend=Trend.up,
                method=CalcMethod.activity,
                spark=[0.9, 1.0, 0.95, 1.05, 1.0, 1.1],
                confidence=0.95,
            ),
            CategoryBreakdown(
                category=Category.energy,
                tco2e=0.8,
                delta_pct=-11,
                trend=Trend.down,
                method=CalcMethod.activity,
                spark=[1.0, 0.98, 0.92, 0.88, 0.85, 0.8],
                confidence=0.95,
            ),
            CategoryBreakdown(
                category=Category.food,
                tco2e=0.6,
                delta_pct=0,
                trend=Trend.flat,
                method=CalcMethod.spend,
                spark=[0.6, 0.61, 0.59, 0.6, 0.6, 0.6],
                confidence=0.8,
            ),
            CategoryBreakdown(
                category=Category.spend,
                tco2e=1.7,
                delta_pct=-6,
                trend=Trend.down,
                method=CalcMethod.spend,
                spark=[1.9, 1.85, 1.8, 1.78, 1.72, 1.7],
                confidence=0.8,
            ),
        ],
    )


def seed_nudges() -> list[Nudge]:
    return [
        Nudge(
            id="n-ev-offpeak",
            kind=NudgeKind.clean_window,
            title="Clean-energy window until 4pm",
            detail="Shift your EV charge to now — the grid is running on renewables.",
            carbon_saved_tco2e=0.0018,
            money_saved=0.80,
            currency="GBP",
            effort=NudgeEffort.one_tap,
            window_ends_at=datetime(2026, 6, 17, 16, 0, tzinfo=timezone.utc),
        ),
        Nudge(
            id="n-tariff",
            kind=NudgeKind.action,
            title="Switch to a renewable tariff",
            detail="Your usage pattern fits a green tariff with no standing-charge hit.",
            carbon_saved_tco2e=0.3,
            money_saved=140,
            currency="GBP",
            effort=NudgeEffort.five_min,
        ),
        Nudge(
            id="n-shipping",
            kind=NudgeKind.default_swap,
            title="Default deliveries to no-rush shipping",
            detail="Consolidated shipping cuts freight emissions on most orders.",
            carbon_saved_tco2e=0.12,
            money_saved=0,
            currency="GBP",
            effort=NudgeEffort.one_tap,
        ),
    ]


def seed_benchmark() -> Benchmark:
    return Benchmark(
        you_tco2e=4.2,
        average_tco2e=4.6,
        top_tco2e=3.1,
        vs_average_pct=-8,
        cohort_size=1840,
    )


def seed_connections() -> list[DataConnection]:
    return [
        DataConnection(id="bank", label="Bank", status="connected", last_sync="2h ago"),
        DataConnection(
            id="telematics", label="Travel", status="connected", last_sync="12m ago"
        ),
        DataConnection(id="meter", label="Home energy", status="needs-attention"),
    ]
