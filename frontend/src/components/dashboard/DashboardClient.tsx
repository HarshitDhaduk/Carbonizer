"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { FootprintSummary } from "@/lib/types";
import { ApiError } from "@/lib/client-api";
import { queries, queryKeys } from "@/lib/queries";
import { useAuthStore } from "@/store/auth-store";
import { AppShell } from "@/components/layout/AppShell";
import { AccountMenu } from "@/components/layout/AccountMenu";
import { DashboardView } from "./DashboardView";
import { ConnectSources } from "@/components/connections/ConnectSources";

/**
 * The authenticated, per-user dashboard. Auth state in HttpOnly cookies; data
 * fetching via TanStack Query (Phase 4.2) so the three parallel fetches share
 * cache, dedup across pages, and refetch on focus without bespoke useEffect
 * plumbing.
 */
export function DashboardClient() {
  const user = useAuthStore((s) => s.user);
  const hydrated = useAuthStore((s) => s.hydrated);
  const loadMe = useAuthStore((s) => s.loadMe);
  const router = useRouter();
  const qc = useQueryClient();

  useEffect(() => {
    void loadMe();
  }, [loadMe]);

  useEffect(() => {
    if (hydrated && !user) router.replace("/onboarding");
  }, [hydrated, user, router]);

  const enabled = hydrated && !!user;
  const summary = useQuery({ ...queries.footprintSummary(), enabled });
  const nudges = useQuery({ ...queries.recommendations(), enabled });
  const benchmark = useQuery({ ...queries.benchmark(), enabled });

  // Surface a 401 from any of the three fetches by clearing local auth and
  // bouncing to onboarding — the cookie has expired or been revoked.
  const anyError = summary.error ?? nudges.error ?? benchmark.error;
  useEffect(() => {
    if (anyError instanceof ApiError && anyError.status === 401) {
      void useAuthStore.getState().logout();
      router.replace("/onboarding");
    }
  }, [anyError, router]);

  function onConnected(next: FootprintSummary) {
    // Optimistic write-through; the next focus-revalidate will reconcile
    // against the server's recomputed snapshot.
    qc.setQueryData(queryKeys.footprint.summary(), next);
    void qc.invalidateQueries({ queryKey: queryKeys.footprint.all });
    void qc.invalidateQueries({ queryKey: queryKeys.connections() });
  }

  if (!hydrated)
    return (
      <AppShell>
        <DashboardSkeleton />
      </AppShell>
    );
  if (!user) return null; // redirecting

  const loading = summary.isPending || nudges.isPending || benchmark.isPending;
  const errMsg =
    !loading && anyError && !(anyError instanceof ApiError && anyError.status === 401)
      ? anyError instanceof Error
        ? anyError.message
        : "Couldn't load your dashboard."
      : null;

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="font-display text-xl text-text-hi">Dashboard</h1>
        <AccountMenu />
      </div>

      {errMsg ? (
        <p role="alert" className="text-sm text-danger">
          {errMsg}
        </p>
      ) : loading || !summary.data || !nudges.data || !benchmark.data ? (
        <DashboardSkeleton />
      ) : (
        <div className="space-y-4">
          <DashboardView
            summary={summary.data}
            topNudge={nudges.data[0]}
            benchmark={benchmark.data}
          />
          <section aria-label="Connect data sources" className="space-y-2">
            <h2 className="text-sm font-medium text-text-mid">
              Improve your accuracy
            </h2>
            <ConnectSources onSummary={onConnected} />
          </section>
        </div>
      )}
    </AppShell>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      <div className="skeleton h-14 rounded-lg" />
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="skeleton h-[340px] rounded-card" />
        <div className="grid grid-cols-2 gap-2.5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-28 rounded-md" />
          ))}
        </div>
      </div>
      <div className="skeleton h-20 rounded-lg" />
    </div>
  );
}
