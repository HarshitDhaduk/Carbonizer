"""Day-0 footprint estimator (docs/DATA-STRATEGY.md §4).

Converts onboarding questionnaire answers into a `FootprintSummary` whose categories are
all `method=estimated`. Coefficients are DEFRA / CoolClimate-style order-of-magnitude
figures (annualized tonnes CO2e) — intentionally rough; measured sources later upgrade
each category to `spend`/`activity`. The questionnaire is defined here so the API and the
estimation model share one source of truth.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.enums import BiomeStatus, CalcMethod, Category, Trend
from app.schemas.footprint import CategoryBreakdown, FootprintSummary
from app.schemas.onboarding import (
    AnswerValue,
    Question,
    QuestionOption,
    Questionnaire,
    VisibleIf,
)

QUESTIONNAIRE_VERSION = 2

# --- questionnaire definition (server-owned; the client renders from this) ---------
# Ordered by value-of-information: the largest footprint drivers first (transport,
# diet) so we get strong early signal and can keep the flow short. `visibleIf` skips
# irrelevant questions (e.g. car km when the user has no car).

QUESTIONS: list[Question] = [
    Question(
        id="carType", type="single", label="Your main car", default="petrol",
        help="Pick the one you use most. No car? We'll skip the rest of this.",
        options=[
            QuestionOption(value="none", label="No car"),
            QuestionOption(value="petrol", label="Petrol"),
            QuestionOption(value="diesel", label="Diesel"),
            QuestionOption(value="hybrid", label="Hybrid"),
            QuestionOption(value="ev", label="Electric"),
        ],
    ),
    Question(
        id="carKmPerWeek", type="number", label="How far do you drive a week?",
        min=0, max=2000, step=10, default=100, unit="km",
        help="A rough typical week is fine.",
        visible_if=VisibleIf(question_id="carType", not_equals="none"),
    ),
    Question(
        id="shortFlightsPerYear", type="number",
        label="Short flights a year", min=0, max=50, step=1, default=1,
        help="Return trips under ~4 hours (e.g. within Europe).",
    ),
    Question(
        id="longFlightsPerYear", type="number",
        label="Long-haul flights a year", min=0, max=30, step=1, default=0,
        help="Return trips over ~4 hours (e.g. intercontinental).",
    ),
    Question(
        id="diet", type="single", label="Your diet", default="average",
        options=[
            QuestionOption(value="meat_heavy", label="Meat with most meals"),
            QuestionOption(value="average", label="Average"),
            QuestionOption(value="low_meat", label="Low meat"),
            QuestionOption(value="vegetarian", label="Vegetarian"),
            QuestionOption(value="vegan", label="Vegan"),
        ],
    ),
    Question(
        id="homeType", type="single", label="Your home", default="terraced",
        options=[
            QuestionOption(value="flat", label="Flat"),
            QuestionOption(value="terraced", label="Terraced"),
            QuestionOption(value="semi", label="Semi-detached"),
            QuestionOption(value="detached", label="Detached"),
        ],
    ),
    Question(
        id="energySource", type="single", label="Home energy", default="standard",
        help="A green tariff or your own solar lowers your electricity emissions.",
        options=[
            QuestionOption(value="standard", label="Standard tariff"),
            QuestionOption(value="green", label="Green tariff"),
            QuestionOption(value="renewable", label="Mostly my own renewable"),
        ],
    ),
    Question(
        id="householdSize", type="number", label="People in your household",
        min=1, max=12, step=1, default=2,
        help="Home energy is shared across everyone who lives with you.",
    ),
]

_QUESTION_BY_ID = {q.id: q for q in QUESTIONS}


def is_visible(q: Question, answers: dict[str, AnswerValue]) -> bool:
    """Whether a question is relevant given the answers so far (mirrors the
    frontend `isVisible`)."""
    cond = q.visible_if
    if cond is None:
        return True
    other = answers.get(cond.question_id)
    if cond.equals is not None:
        return other == cond.equals
    if cond.not_equals is not None:
        return other != cond.not_equals
    if cond.any_of is not None:
        return other in cond.any_of
    return True

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


def build_questionnaire() -> Questionnaire:
    return Questionnaire(version=QUESTIONNAIRE_VERSION, questions=QUESTIONS)


def normalize_answers(raw: dict[str, AnswerValue]) -> dict[str, AnswerValue]:
    """Fill defaults, validate option keys, clamp numbers. Forgiving by design."""
    out: dict[str, AnswerValue] = {}
    for q in QUESTIONS:
        val = raw.get(q.id, q.default)
        if q.type == "number":
            try:
                num = int(val)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                num = int(q.default)  # type: ignore[arg-type]
            if q.min is not None:
                num = max(q.min, num)
            if q.max is not None:
                num = min(q.max, num)
            out[q.id] = num
        else:  # single-choice
            valid = {o.value for o in (q.options or [])}
            out[q.id] = val if val in valid else q.default

    # neutralize hidden questions (e.g. car km when carType == none) so an
    # irrelevant leftover answer can't contribute to the estimate
    for q in QUESTIONS:
        if not is_visible(q, out):
            out[q.id] = 0 if q.type == "number" else q.default
    return out


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
        generated_at=datetime.now(timezone.utc),
    )


# --- R0: value-of-information ordering ---------------------------------------------
# Score each question by how much its answer can swing the total footprint (holding
# the rest at defaults) — its information content. Order questions by that score,
# highest-yield first, so the flow front-loads the questions that most shrink the
# user's footprint uncertainty (docs/DATA-STRATEGY.md §9, R0; composes with R1).


def _question_spread(q: Question) -> float:
    """Total-footprint spread (tCO2e) as `q` varies over its domain, others fixed."""
    base: dict[str, AnswerValue] = {qq.id: qq.default for qq in QUESTIONS}
    totals: list[float] = []
    if q.type == "single":
        for opt in q.options or []:
            totals.append(estimate({**base, q.id: opt.value}).total_tco2e)
    else:
        lo, hi = q.min or 0, q.max if q.max is not None else 0
        for v in (lo, hi):
            totals.append(estimate({**base, q.id: v}).total_tco2e)
    return (max(totals) - min(totals)) if totals else 0.0


def _voi_order(questions: list[Question]) -> list[Question]:
    """Sort by VoI desc, but keep each question after its `visible_if` parent."""
    by_voi = sorted(questions, key=lambda q: q.voi or 0, reverse=True)
    by_id = {q.id: q for q in questions}
    placed: set[str] = set()
    result: list[Question] = []

    def place(q: Question) -> None:
        if q.id in placed:
            return
        parent_id = q.visible_if.question_id if q.visible_if else None
        if parent_id and parent_id in by_id:
            place(by_id[parent_id])
        placed.add(q.id)
        result.append(q)

    for q in by_voi:
        place(q)
    return result


def _apply_voi() -> None:
    spreads = {q.id: _question_spread(q) for q in QUESTIONS}
    mx = max(spreads.values()) or 1.0
    for q in QUESTIONS:
        q.voi = round(spreads[q.id] / mx, 3)
    QUESTIONS[:] = _voi_order(QUESTIONS)


_apply_voi()
