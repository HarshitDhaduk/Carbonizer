import { clientApi } from "./client-api";

/**
 * Canonical query keys + factories — Phase 4.2 of docs/IMPROVEMENT-PLAN.md.
 *
 * Centralizing keys here lets us invalidate by namespace ("after a bank
 * link, refresh anything that depends on the footprint") instead of
 * scattering string literals across components. The factory shape mirrors
 * TanStack's recommended pattern so a key never accidentally collides
 * across two callers that intend different scopes.
 */
export const queryKeys = {
  me: ["auth", "me"] as const,
  footprint: {
    all: ["footprint"] as const,
    summary: (range = "12w") => ["footprint", "summary", range] as const,
    attribution: () => ["footprint", "attribution"] as const,
  },
  recommendations: () => ["recommendations"] as const,
  benchmark: () => ["community", "benchmark"] as const,
  connections: () => ["connections"] as const,
  onboarding: {
    questions: () => ["onboarding", "questions"] as const,
    profile: () => ["onboarding", "profile"] as const,
  },
};

/** Query option helpers — keep call-site code declarative. */
export const queries = {
  footprintSummary: (range = "12w") => ({
    queryKey: queryKeys.footprint.summary(range),
    queryFn: () => clientApi.getFootprintSummary(range),
  }),
  attribution: () => ({
    queryKey: queryKeys.footprint.attribution(),
    queryFn: () => clientApi.getAttribution(),
  }),
  recommendations: () => ({
    queryKey: queryKeys.recommendations(),
    queryFn: () => clientApi.getRecommendations(),
  }),
  benchmark: () => ({
    queryKey: queryKeys.benchmark(),
    queryFn: () => clientApi.getBenchmark(),
  }),
  connections: () => ({
    queryKey: queryKeys.connections(),
    queryFn: () => clientApi.getConnections(),
  }),
  me: () => ({
    queryKey: queryKeys.me,
    queryFn: () => clientApi.getMe(),
  }),
  onboardingQuestions: () => ({
    queryKey: queryKeys.onboarding.questions(),
    queryFn: () => clientApi.getOnboardingQuestions(),
  }),
  onboardingProfile: () => ({
    queryKey: queryKeys.onboarding.profile(),
    queryFn: () => clientApi.getOnboardingProfile(),
  }),
};
