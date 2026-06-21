"""Day-0 footprint estimator (docs/DATA-STRATEGY.md §4).

Pure function: normalized questionnaire answers → ``FootprintSummary`` whose
categories are all ``method=estimated``. Coefficients are DEFRA / CoolClimate-
style order-of-magnitude figures (annualized tonnes CO2e) — intentionally
rough; measured sources later upgrade each category to ``spend`` / ``activity``.

The questionnaire data + visibility helpers live in
:mod:`app.services.questionnaire`. The value-of-information ordering lives in
:mod:`app.services.voi`. Both are re-exported here for back-compat with
``from app.services import estimator`` callers.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.enums import BiomeStatus, CalcMethod, Category, Trend
from app.schemas.footprint import CategoryBreakdown, FootprintSummary
from app.schemas.onboarding import AnswerValue
from app.services.questionnaire import (
    QUESTIONNAIRE_VERSION,
    QUESTIONS,
    build_questionnaire,
    is_visible,
    normalize_answers,
)
from app.services.voi import apply_voi

__all__ = [
    "QUESTIONNAIRE_VERSION",
    "QUESTIONS",
    "build_questionnaire",
    "estimate",
    "health_for_total",
    "is_visible",
    "normalize_answers",
    "status_for_health",
]


# --- coefficients (annual tonnes CO2e) ---------------------------------------------

_CAR_KG_PER_KM = {"none": 0.0, "petrol": 0.170, "diesel": 0.165, "hybrid": 0.110, "ev": 0.050}
_FLIGHT_TCO2E = {"short": 0.30, "long": 1.80}  # per return flight (incl. radiative forcing)
_HOME_ENERGY_TCO2E = {"flat": 1.8, "terraced": 2.6, "semi": 3.2, "detached": 4.5}
_ENERGY_SOURCE_FACTOR = {"standard": 1.0, "green": 0.6, "renewable": 0.4}
_DIET_TCO2E = {"meat_heavy": 2.5, "average": 2.0, "low_meat": 1.7, "vegetarian": 1.4, "vegan": 1.1}
_SPEND_BASE_TCO2E = {"flat": 1.2, "terraced": 1.4, "semi": 1.6, "detached": 2.0}

# health scale: total CO2e mapped to 0..1 (lower footprint → healthier biome)
_HEALTH_LOW_T = 2.0   # excellent
_HEALTH_HIGH_T = 15.0  # poor


def health_for_total(total_tco2e: float) -> float:
    """Map an annual footprint (tCO2e) to biome health 0..1 (lower = healthier)."""
    return max(
        0.0,
        min(1.0, (_HEALTH_HIGH_T - total_tco2e) / (_HEALTH_HIGH_T - _HEALTH_LOW_T)),
    )


def status_for_health(health: float) -> BiomeStatus:
    if health >= 0.66:
        return BiomeStatus.thriving
    if health >= 0.45:
        return BiomeStatus.improving
    if health >= 0.30:
        return BiomeStatus.plateau
    if health >= 0.15:
        return BiomeStatus.regressing
    return BiomeStatus.seed


def _category(cat: Category, tco2e: float) -> CategoryBreakdown:
    v = round(tco2e, 2)
    return CategoryBreakdown(
        category=cat,
        tco2e=v,
        delta_pct=0.0,          # no history on a Day-0 estimate
        trend=Trend.flat,
        method=CalcMethod.estimated,
        spark=[v] * 6,          # flat line until measured data arrives
        confidence=0.30,        # R1: flat onboarding estimate → low confidence
    )


def estimate(answers: dict[str, AnswerValue]) -> FootprintSummary:
    """Pure function: normalized answers → FootprintSummary (all categories estimated)."""
    a = normalize_answers(answers)

    household = max(1, int(a["householdSize"]))
    home = str(a["homeType"])
    energy_src = str(a["energySource"])
    diet = str(a["diet"])
    car = str(a["carType"])
    car_km_year = int(a["carKmPerWeek"]) * 52
    short_flights = int(a["shortFlightsPerYear"])
    long_flights = int(a["longFlightsPerYear"])

    # transport: personal car + flights
    car_t = car_km_year * _CAR_KG_PER_KM.get(car, 0.170) / 1000
    flights_t = short_flights * _FLIGHT_TCO2E["short"] + long_flights * _FLIGHT_TCO2E["long"]
    transport = car_t + flights_t

    # energy: household total, attributed per person with mild economy of scale
    energy_household = _HOME_ENERGY_TCO2E.get(home, 2.6) * _ENERGY_SOURCE_FACTOR.get(energy_src, 1.0)
    energy = energy_household / (household**0.7)

    # food: per-person diet
    food = _DIET_TCO2E.get(diet, 2.0)

    # spend: baseline goods/services not captured above (home type as a wealth proxy)
    spend = _SPEND_BASE_TCO2E.get(home, 1.4)

    categories = [
        _category(Category.transport, transport),
        _category(Category.energy, energy),
        _category(Category.food, food),
        _category(Category.spend, spend),
    ]
    total = round(sum(c.tco2e for c in categories), 2)

    health = health_for_total(total)
    target = round(max(_HEALTH_LOW_T, total * 0.75), 1)

    return FootprintSummary(
        total_tco2e=total,
        delta_pct=0.0,
        trend=Trend.flat,
        status=status_for_health(health),
        target_tco2e=target,
        health=round(health, 3),
        categories=categories,
        range="12w",
        generated_at=datetime.now(UTC),
    )


# Apply VoI scoring + ordering once at module load. The estimator passes itself
# in so voi.py stays a pure helper module with no circular import.
apply_voi(QUESTIONS, estimate)
