"""R4 — privacy-preserving + selection-bias-corrected benchmarking
(docs/DATA-STRATEGY.md §9).

Two corrections sit between the raw cohort and the "you vs average" the user sees:

1. **Selection-bias correction (MNAR / IPW).** The users who connect data self-select
   toward lower footprints (eco-keen). A naive cohort mean therefore *understates* the
   true population, making everyone look worse than they are. Reweighting each connected
   user by 1/P(connect | features) lifts the estimate toward the unbiased population.

2. **Differential privacy.** A published cohort mean can leak an individual; the Laplace
   mechanism adds calibrated noise for an (ε)-DP release. We draw it deterministically
   per cohort so the figure is stable across requests rather than re-leaking each call.

Both are MVPs: `_SELECTION_SKEW` stands in for learned propensity scores, and the DP
mechanism is the real Laplace release (the seam where secure aggregation plugs in).
"""

from __future__ import annotations

import math
import random

# population mean ≈ 10% above the eco-keen connectors' mean (placeholder for the
# inverse-propensity reweighting once real connect-propensity scores are learned).
_SELECTION_SKEW = 1.10

# Laplace DP parameters for a published cohort mean (tCO2e)
DP_EPSILON = 1.0
DP_SENSITIVITY = 0.1  # bounded per-record influence on the mean


def ipw_population_mean(observed_mean: float) -> float:
    """Inverse-propensity-weighted estimate of the *population* mean from the
    eco-skewed sample of users who connected data."""
    return observed_mean * _SELECTION_SKEW


def laplace_dp(
    value: float,
    seed: int,
    epsilon: float = DP_EPSILON,
    sensitivity: float = DP_SENSITIVITY,
) -> float:
    """(ε)-differentially-private release via the Laplace mechanism, deterministic
    per `seed` so repeated reads return the same protected figure."""
    rng = random.Random(seed)
    scale = sensitivity / epsilon
    u = rng.random() - 0.5
    noise = -scale * math.copysign(1.0, u) * math.log(1 - 2 * abs(u))
    return value + noise


def adjusted_average(observed_mean: float, cohort_seed: int) -> float:
    """Selection-bias-corrected, DP-protected cohort mean for display."""
    pop = ipw_population_mean(observed_mean)
    return round(laplace_dp(pop, cohort_seed), 1)
