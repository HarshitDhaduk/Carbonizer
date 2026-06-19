"""R1 — Open Banking as a "hub view": impute unmeasured categories.

Most users connect only their bank. The bank still *partially observes* the other
categories — total spend is an affluence/activity signal correlated with how much a
household drives and heats. When a category has no direct transactions (no fuel, no
utility direct-debit), we reconstruct it from the bank signal + the onboarding
demographics instead of leaving the flat Day-0 estimate, and attach a calibrated
**confidence**.

This is the heuristic MVP: the blend weights below would be *learned* from the
"anchor set" — the minority of users who connect all three sources — so the model
de-biases the single-source majority (docs/DATA-STRATEGY.md §9, R1). The function
signature is the seam where that learned model drops in.
"""

from __future__ import annotations

from app.models.enums import CalcMethod

# calibrated confidence by data quality (the "posterior" precision)
CONFIDENCE: dict[CalcMethod, float] = {
    CalcMethod.activity: 0.95,  # metered / measured physical quantity
    CalcMethod.spend: 0.80,     # spend-based from real transactions
    CalcMethod.estimated: 0.30,  # flat onboarding estimate, no bank signal
}
IMPUTED_CONFIDENCE = 0.55  # bank-informed reconstruction — better than flat, not measured

# reference monthly discretionary spend the relationship is anchored at
_REF_MONTHLY_GBP = 1500.0


def impute_from_bank(
    prior_tco2e: float, monthly_spend_gbp: float
) -> tuple[float, float]:
    """Refine a flat category estimate using the bank's total-spend signal.

    Returns (tco2e, confidence). Higher overall spend nudges the category up toward
    the population relationship between affluence and transport/energy use; the blend
    keeps 60% of the onboarding estimate so it can't run away on the bank signal alone.
    """
    signal = max(0.5, min(1.8, monthly_spend_gbp / _REF_MONTHLY_GBP))
    imputed = prior_tco2e * (0.6 + 0.4 * signal)
    return round(imputed, 2), IMPUTED_CONFIDENCE
