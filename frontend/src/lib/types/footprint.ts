/**
 * Footprint + attribution domain types. Mirrors the FastAPI ``FootprintSummary``
 * and ``Attribution`` schemas one-for-one (docs/API-DESIGN.md §3).
 */

export type Category = "transport" | "energy" | "food" | "spend" | "home";

/** Trend direction relative to the prior period. */
export type Trend = "up" | "down" | "flat";

/** How an emission figure was derived (docs/DESIGN.md §2). */
export type Method = "activity" | "spend" | "estimated";

/** Overall biome / footprint health, interpolated 0..1 (0 = poor, 1 = thriving). */
export type BiomeStatus =
  | "seed"
  | "regressing"
  | "plateau"
  | "improving"
  | "thriving";

export interface CategoryBreakdown {
  category: Category;
  /** tonnes CO2e for the active period. */
  tco2e: number;
  /** signed % change vs previous period. */
  deltaPct: number;
  trend: Trend;
  method: Method;
  /** small sparkline series, oldest → newest. */
  spark: number[];
  /** R1: calibrated confidence 0..1 (activity ≈ 0.95 → estimated ≈ 0.3). */
  confidence?: number;
  /** R1: reconstructed from the bank "hub" rather than directly measured. */
  imputed?: boolean;
}

/** R3 — energy ΔCO₂e split into behavioral (usage) vs structural (grid). */
export interface Attribution {
  available: boolean;
  periodDays: number;
  totalDeltaKg: number;
  behavioralKg: number;
  structuralKg: number;
  /** |behavioral| / (|behavioral| + |structural|), 0..1. */
  behaviorShare: number;
}

export interface FootprintSummary {
  /** annualized total, tonnes CO2e. */
  totalTco2e: number;
  /** signed % change vs the previous period. */
  deltaPct: number;
  trend: Trend;
  status: BiomeStatus;
  /** personalized target the biome measures against (tonnes CO2e / yr). */
  targetTco2e: number;
  /** 0..1 normalized health used to drive the 3D biome. */
  health: number;
  categories: CategoryBreakdown[];
}
