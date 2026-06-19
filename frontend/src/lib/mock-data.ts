import type {
  Benchmark,
  DataConnection,
  FootprintSummary,
  Nudge,
} from "./types";

/**
 * Mock data so the UI runs before the FastAPI backend exists.
 * Mirrors the dashboard mockup in docs/UI-UX-DESIGN.md §6.2.
 * Swap these for `src/lib/api.ts` calls once endpoints land.
 */

export const MOCK_SUMMARY: FootprintSummary = {
  totalTco2e: 4.2,
  deltaPct: -8,
  trend: "down",
  status: "improving",
  targetTco2e: 3.5,
  health: 0.62,
  categories: [
    {
      category: "transport",
      tco2e: 1.1,
      deltaPct: 4,
      trend: "up",
      method: "activity",
      spark: [0.9, 1.0, 0.95, 1.05, 1.0, 1.1],
    },
    {
      category: "energy",
      tco2e: 0.8,
      deltaPct: -11,
      trend: "down",
      method: "activity",
      spark: [1.0, 0.98, 0.92, 0.88, 0.85, 0.8],
    },
    {
      category: "food",
      tco2e: 0.6,
      deltaPct: 0,
      trend: "flat",
      method: "spend",
      spark: [0.6, 0.61, 0.59, 0.6, 0.6, 0.6],
    },
    {
      category: "spend",
      tco2e: 1.7,
      deltaPct: -6,
      trend: "down",
      method: "spend",
      spark: [1.9, 1.85, 1.8, 1.78, 1.72, 1.7],
    },
  ],
};

export const MOCK_NUDGE: Nudge = {
  id: "n-ev-offpeak",
  kind: "clean-window",
  title: "Clean-energy window until 4pm",
  detail: "Shift your EV charge to now — the grid is running on renewables.",
  carbonSavedTco2e: 0.0018,
  moneySaved: 0.8,
  currency: "GBP",
  effort: "1-tap",
  windowEndsAt: "2026-06-17T16:00:00Z",
};

export const MOCK_NUDGES: Nudge[] = [
  MOCK_NUDGE,
  {
    id: "n-tariff",
    kind: "action",
    title: "Switch to a renewable tariff",
    detail: "Your usage pattern fits a green tariff with no standing-charge hit.",
    carbonSavedTco2e: 0.3,
    moneySaved: 140,
    currency: "GBP",
    effort: "5-min",
  },
  {
    id: "n-shipping",
    kind: "default-swap",
    title: "Default deliveries to no-rush shipping",
    detail: "Consolidated shipping cuts freight emissions on most orders.",
    carbonSavedTco2e: 0.12,
    moneySaved: 0,
    currency: "GBP",
    effort: "1-tap",
  },
];

export const MOCK_BENCHMARK: Benchmark = {
  youTco2e: 4.2,
  averageTco2e: 4.6,
  topTco2e: 3.1,
  vsAveragePct: -8,
};

export const MOCK_CONNECTIONS: DataConnection[] = [
  { id: "bank", label: "Bank", status: "connected", lastSync: "2h ago" },
  { id: "telematics", label: "Travel", status: "connected", lastSync: "12m ago" },
  { id: "meter", label: "Home energy", status: "needs-attention" },
];
