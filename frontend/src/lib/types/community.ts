/** Cohort benchmark domain types — R4 (IPW + Laplace DP + k-anonymity). */

export interface Benchmark {
  /** the user's annualized footprint, tonnes CO2e. */
  youTco2e: number;
  /** cohort average (similar household size + income). */
  averageTco2e: number;
  /** cohort top-20% threshold. */
  topTco2e: number;
  /** signed % the user is relative to the average (negative = below/better). */
  vsAveragePct: number;
  /** cohort size, suppressed (omitted/null) below the k-anonymity threshold. */
  cohortSize?: number | null;
  /** R4: average is selection-bias-corrected (IPW) + differentially-private. */
  privacyAdjusted?: boolean;
}
