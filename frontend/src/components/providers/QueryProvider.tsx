"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

/**
 * App-wide React Query provider (Phase 4.2 of docs/IMPROVEMENT-PLAN.md).
 *
 * Defaults
 *   * `staleTime: 30s` — keeps the dashboard from refetching identical data
 *     on every tab focus inside a workflow.
 *   * `gcTime: 5min` — drops cache entries after the user moves on, so a stale
 *     summary can't reappear if they wander back.
 *   * `refetchOnWindowFocus: true` — the dashboard moves with real-world
 *     activity (a new bank transaction lands while the tab is idle); refresh
 *     on return so the user always sees their latest.
 *   * `retry: 1` — auth errors should surface immediately; one retry covers
 *     a transient network hiccup without amplifying outages.
 *
 * `useState` for the client ensures a single instance survives React strict
 * mode's double-mount in development and Next 16's server-component reuse.
 */
export function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            gcTime: 5 * 60 * 1000,
            refetchOnWindowFocus: true,
            retry: 1,
          },
          mutations: { retry: 0 },
        },
      }),
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
