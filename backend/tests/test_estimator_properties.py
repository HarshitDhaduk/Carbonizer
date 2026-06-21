"""Hypothesis property-based tests for the onboarding estimator (Phase 3.5).

Example-based tests catch the bug you're already thinking about; property tests
catch the bug nobody's thought of. The estimator is a pure function with clear
invariants, so it's a natural fit.

Invariants we pin down here:

  1. **Total is the sum of categories.** No matter how the answers wiggle,
     ``sum(categories) == total_tco2e`` (within float rounding).
  2. **Health is bounded.** ``health`` ∈ [0, 1] for any input — visualised on
     a 0..100 ring on the dashboard.
  3. **Categories are non-negative.** A footprint isn't a credit.
  4. **No car ⇒ transport is bounded above by an equivalent has-car answer.**
     The "carType=none, carKmPerWeek=anything" path should never out-emit
     someone driving petrol.
  5. **Normalisation is idempotent.** ``normalize(normalize(x)) == normalize(x)``
     — keeps the autosave pipeline safe to replay.
  6. **Status maps monotonically from health.** Higher health never demotes
     the biome status to a worse band.

These run on the no-DB pure path, so they're fast (a few hundred ms for ~100
examples each).
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.enums import BiomeStatus
from app.services import estimator

_CAR_TYPES = ["none", "petrol", "diesel", "hybrid", "ev"]
_DIETS = ["meat_heavy", "average", "low_meat", "vegetarian", "vegan"]
_HOMES = ["flat", "terraced", "semi", "detached"]
_ENERGY_SOURCES = ["standard", "green", "renewable"]

# Plausible-but-broad answer space. The estimator clamps to declared bounds,
# so we explore around them: feed values within the questionnaire ranges plus a
# little slack so we hit the clamp path too.
_answers = st.fixed_dictionaries(
    {
        "carType": st.sampled_from(_CAR_TYPES),
        "carKmPerWeek": st.integers(min_value=0, max_value=2500),
        "shortFlightsPerYear": st.integers(min_value=0, max_value=60),
        "longFlightsPerYear": st.integers(min_value=0, max_value=40),
        "diet": st.sampled_from(_DIETS),
        "homeType": st.sampled_from(_HOMES),
        "energySource": st.sampled_from(_ENERGY_SOURCES),
        "householdSize": st.integers(min_value=1, max_value=15),
    }
)


@given(answers=_answers)
@settings(max_examples=200, deadline=500)
def test_categories_sum_to_total(answers: dict[str, object]) -> None:
    summary = estimator.estimate(answers)  # type: ignore[arg-type]
    assert round(sum(c.tco2e for c in summary.categories), 2) == summary.total_tco2e


@given(answers=_answers)
@settings(max_examples=200, deadline=500)
def test_health_is_bounded(answers: dict[str, object]) -> None:
    summary = estimator.estimate(answers)  # type: ignore[arg-type]
    assert 0.0 <= summary.health <= 1.0


@given(answers=_answers)
@settings(max_examples=200, deadline=500)
def test_categories_non_negative(answers: dict[str, object]) -> None:
    summary = estimator.estimate(answers)  # type: ignore[arg-type]
    for c in summary.categories:
        assert c.tco2e >= 0, f"{c.category}: {c.tco2e}"


@given(
    km=st.integers(min_value=0, max_value=2500),
    short_f=st.integers(min_value=0, max_value=60),
    long_f=st.integers(min_value=0, max_value=40),
)
@settings(max_examples=100, deadline=500)
def test_no_car_caps_transport_below_petrol(
    km: int, short_f: int, long_f: int
) -> None:
    """For matched flights, ``carType=none`` must yield transport ≤ ``carType=petrol``
    at the same km — the normalize step zeroes carKmPerWeek when no car."""
    common = {
        "carKmPerWeek": km,
        "shortFlightsPerYear": short_f,
        "longFlightsPerYear": long_f,
        "diet": "average",
        "homeType": "semi",
        "energySource": "standard",
        "householdSize": 2,
    }
    none_summary = estimator.estimate({"carType": "none", **common})
    petrol_summary = estimator.estimate({"carType": "petrol", **common})

    def transport(summary: object) -> float:
        return next(
            c.tco2e
            for c in summary.categories  # type: ignore[attr-defined]
            if c.category.value == "transport"
        )

    assert transport(none_summary) <= transport(petrol_summary)


@given(answers=_answers)
@settings(max_examples=200, deadline=500)
def test_normalize_is_idempotent(answers: dict[str, object]) -> None:
    once = estimator.normalize_answers(answers)  # type: ignore[arg-type]
    twice = estimator.normalize_answers(once)
    assert once == twice


@given(t1=st.floats(0.0, 20.0), t2=st.floats(0.0, 20.0))
@settings(max_examples=200, deadline=500)
def test_status_is_monotonic_in_health(t1: float, t2: float) -> None:
    """Lower total → higher health → status band that's at least as good.

    The ladder is seed < regressing < plateau < improving < thriving; turning
    the footprint dial down should never move us *down* the ladder.
    """
    order: dict[BiomeStatus, int] = {
        BiomeStatus.seed: 0,
        BiomeStatus.regressing: 1,
        BiomeStatus.plateau: 2,
        BiomeStatus.improving: 3,
        BiomeStatus.thriving: 4,
    }
    h1 = estimator.health_for_total(t1)
    h2 = estimator.health_for_total(t2)
    s1 = estimator.status_for_health(h1)
    s2 = estimator.status_for_health(h2)
    if h1 >= h2:
        assert order[s1] >= order[s2]
    else:
        assert order[s1] <= order[s2]
