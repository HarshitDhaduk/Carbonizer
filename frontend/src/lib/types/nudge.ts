/** Nudge / recommendation domain types. */

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
