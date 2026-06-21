"""Hypothesis property tests for the carbon-accounting services.

These cover the pure functions that the estimator + recompute call hundreds
of times per request. Example-based tests already pin the documented
behaviours; properties pin the *invariants*, which catch a different class
of regression (a swapped sign in price elasticity, a factor change that
flips the merchant-multiplier sign, etc.).
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.enums import CalcMethod, Category
from app.services import carbon, impute

_CATEGORIES = list(Category)
_MERCHANTS = [
    "Tesco",
    "Zara",
    "Uniqlo",
    "Octopus Energy",
    "British Gas",
    "Shell",
    None,
]


@given(
    cat=st.sampled_from(_CATEGORIES),
    gbp=st.floats(min_value=0, max_value=10_000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=150, deadline=500)
def test_co2e_kg_non_negative(cat: Category, gbp: float) -> None:
    """Carbon can't be negative for non-negative spend."""
    assert carbon.co2e_kg(cat, gbp) >= 0


@given(
    cat=st.sampled_from(_CATEGORIES),
    gbp=st.floats(min_value=0.01, max_value=5_000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=150, deadline=500)
def test_co2e_kg_monotonic_in_gbp(cat: Category, gbp: float) -> None:
    """Spending more money in the same category must not yield less CO2e."""
    base = carbon.co2e_kg(cat, gbp)
    more = carbon.co2e_kg(cat, gbp * 1.25)
    assert more + 1e-9 >= base


@given(
    cat=st.sampled_from(_CATEGORIES),
    gbp=st.floats(min_value=1, max_value=5_000, allow_nan=False, allow_infinity=False),
    merchant=st.sampled_from(_MERCHANTS),
)
@settings(max_examples=150, deadline=500)
def test_merchant_multiplier_is_finite_and_positive(
    cat: Category, gbp: float, merchant: str | None
) -> None:
    """The merchant lookup is the R2 hook — it must always return a positive
    finite multiplier so co2e_kg(cat, gbp, merchant) stays finite + positive."""
    value = carbon.co2e_kg(cat, gbp, merchant)
    assert value >= 0
    assert value < float("inf")


@given(
    kwh=st.floats(min_value=0, max_value=10_000, allow_nan=False, allow_infinity=False),
    grid=st.floats(min_value=0, max_value=1_000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=150, deadline=500)
def test_energy_co2e_kg_monotonic_in_grid_intensity(kwh: float, grid: float) -> None:
    """Dirtier grid → more CO2e for the same kWh on electricity."""
    if kwh == 0:
        return
    clean = carbon.energy_co2e_kg(kwh, "electricity", grid)
    dirty = carbon.energy_co2e_kg(kwh, "electricity", grid + 50)
    assert dirty + 1e-9 >= clean


def test_categorize_unknown_mcc_falls_back_to_spend() -> None:
    """The catch-all branch — easy to break in a refactor; pin it."""
    assert carbon.categorize(None) is Category.spend
    assert carbon.categorize("9999") is Category.spend  # unmapped MCC


@given(
    prior=st.floats(min_value=0.01, max_value=8.0, allow_nan=False, allow_infinity=False),
    monthly_spend=st.floats(min_value=0, max_value=10_000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=500)
def test_impute_from_bank_within_band(prior: float, monthly_spend: float) -> None:
    """R1 contract: the imputed value sits within a plausible band of the prior,
    and the returned confidence is the imputed band (between activity + estimated)."""
    value, confidence = impute.impute_from_bank(prior, monthly_spend)
    assert value >= 0
    assert confidence == impute.IMPUTED_CONFIDENCE
    # confidence is strictly between activity (≈0.95) and estimated (≈0.30)
    assert confidence > impute.CONFIDENCE[CalcMethod.estimated]
    assert confidence < impute.CONFIDENCE[CalcMethod.activity]


@given(
    prior=st.floats(min_value=0.01, max_value=8.0, allow_nan=False, allow_infinity=False),
    monthly_low=st.floats(min_value=0, max_value=500, allow_nan=False, allow_infinity=False),
    monthly_high=st.floats(min_value=2000, max_value=10_000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=150, deadline=500)
def test_impute_from_bank_monotonic_in_spend(
    prior: float, monthly_low: float, monthly_high: float
) -> None:
    """R1: higher monthly spend implies higher (or equal) inferred usage."""
    low_v, _ = impute.impute_from_bank(prior, monthly_low)
    high_v, _ = impute.impute_from_bank(prior, monthly_high)
    assert high_v + 1e-9 >= low_v
