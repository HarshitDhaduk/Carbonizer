/**
 * Domain types for Carbonizer — re-exported from focused per-domain modules.
 *
 * Files live under ``./types/`` (footprint, nudge, community, connection,
 * auth, onboarding). This barrel preserves the existing
 * ``import { ... } from "@/lib/types"`` call sites — splitting the modules
 * is a refactor for readers of the source, not a contract change for callers.
 */

export type {
  Attribution,
  BiomeStatus,
  Category,
  CategoryBreakdown,
  FootprintSummary,
  Method,
  Trend,
} from "./types/footprint";
export type { Nudge, NudgeEffort, NudgeKind } from "./types/nudge";
export type { Benchmark } from "./types/community";
export type {
  ConnectProvider,
  ConnectResult,
  DataConnection,
} from "./types/connection";
export type { AuthUser } from "./types/auth";
export type {
  AnswerValue,
  OnboardingAnswers,
  OnboardingProfile,
  OnboardingStatus,
  Question,
  QuestionOption,
  QuestionType,
  Questionnaire,
  VisibleIf,
} from "./types/onboarding";
