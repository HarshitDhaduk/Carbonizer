/**
 * Domain types for Carbonizer. These mirror the FastAPI contract sketched in
 * docs/UI-UX-DESIGN.md §13 and the accounting model in docs/DESIGN.md §2.
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

export type NudgeEffort = "1-tap" | "5-min" | "setup";
export type NudgeKind = "action" | "default-swap" | "clean-window";

export interface Nudge {
  id: string;
  kind: NudgeKind;
  title: string;
  detail: string;
  /** projected annual carbon saving, tonnes CO2e (positive = saved). */
  carbonSavedTco2e: number;
  /** projected annual money saving, in user currency minor→major units. */
  moneySaved: number;
  currency: string;
  effort: NudgeEffort;
  /** for clean-window nudges: ISO end time of the low-carbon window. */
  windowEndsAt?: string;
}

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

export interface DataConnection {
  id: "bank" | "telematics" | "meter";
  label: string;
  status: "disconnected" | "connecting" | "connected" | "needs-attention";
  lastSync?: string;
}

/* ── Auth ──────────────────────────────────────────────────────────────── */

export interface AuthUser {
  id: string;
  email: string;
  region: string;
  targetTco2e: number | null;
}

/* ── Onboarding (docs/API-DESIGN.md §10) ──────────────────────────────────── */

export type QuestionType = "single" | "number";

export interface QuestionOption {
  value: string;
  label: string;
}

/** Show a question only when another answer satisfies this condition. */
export interface VisibleIf {
  questionId: string;
  equals?: AnswerValue;
  notEquals?: AnswerValue;
  anyOf?: AnswerValue[];
}

export interface Question {
  id: string;
  type: QuestionType;
  label: string;
  /** present for `single` questions. */
  options?: QuestionOption[];
  /** present for `number` questions. */
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  /** optional helper text shown under the label. */
  help?: string;
  /** gates visibility on another answer (e.g. car km only if carType ≠ none). */
  visibleIf?: VisibleIf;
  /** R0: value-of-information 0..1 — how much answering shrinks footprint uncertainty. */
  voi?: number;
  default: AnswerValue;
}

export interface Questionnaire {
  version: number;
  questions: Question[];
}

/** A single-choice option key (string) or a numeric answer. */
export type AnswerValue = number | string;

/** Answers keyed by question id. */
export type OnboardingAnswers = Record<string, AnswerValue>;

export type OnboardingStatus = "in_progress" | "completed";

export interface OnboardingProfile {
  status: OnboardingStatus;
  completed: boolean;
  /** the step the user was on — used to resume a half-finished onboarding. */
  currentStep: number;
  answers: OnboardingAnswers | null;
}

/** Result of connecting a (sandbox) data source — docs/API-DESIGN.md §4. */
export interface ConnectResult {
  connection: DataConnection;
  recordsImported: number;
  summary: FootprintSummary;
}

/** Sources the user can connect from the UI. */
export type ConnectProvider = "bank" | "meter";
