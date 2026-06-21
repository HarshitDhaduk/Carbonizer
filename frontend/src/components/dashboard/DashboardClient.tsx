"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { Benchmark, FootprintSummary, Nudge } from "@/lib/types";
import { ApiError, clientApi } from "@/lib/client-api";
import { useAuthStore } from "@/store/auth-store";
import { AppShell } from "@/components/layout/AppShell";
import { AccountMenu } from "@/components/layout/AccountMenu";
import { DashboardView } from "./DashboardView";
import { ConnectSources } from "@/components/connections/ConnectSources";

interface Data {
  summary: FootprintSummary;
  nudges: Nudge[];
  benchmark: Benchmark;
}

/**
 * The authenticated, per-user dashboard. Auth state is held in HttpOnly cookies
 * (see store/auth-store.ts); this component just calls /auth/me on mount and
 * routes unauthenticated visitors back to onboarding.
 */
export function DashboardClient() {
  const user = useAuthStore((s) => s.user);
  const hydrated = useAuthStore((s) => s.hydrated);
  const loadMe = useAuthStore((s) => s.loadMe);
  const router = useRouter();

  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadMe();
  }, [loadMe]);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) {
      router.replace("/onboarding");
      return;
    }
    let active = true;
    Promise.all([
      clientApi.getFootprintSummary(),
      clientApi.getRecommendations(),
      clientApi.getBenchmark(),
    ])
      .then(([summary, nudges, benchmark]) => {
        if (active) setData({ summary, nudges, benchmark });
      })
      .catch(async (e) => {
        if (!active) return;
        if (e instanceof ApiError && e.status === 401) {
          await useAuthStore.getState().logout();
          router.replace("/onboarding");
          return;
        }
        setError(
          e instanceof Error ? e.message : "Couldn't load your dashboard.",
        );
      });
    return () => {
      active = false;
    };
  }, [hydrated, user, router]);

  function onConnected(summary: FootprintSummary) {
    setData((d) => (d ? { ...d, summary } : d));
  }

  if (!hydrated)
    return (
      <AppShell>
        <DashboardSkeleton />
      </AppShell>
    );
  if (!user) return null; // redirecting

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="font-display text-xl text-text-hi">Dashboard</h1>
        <AccountMenu />
      </div>

      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : !data ? (
        <DashboardSkeleton />
      ) : (
        <div className="space-y-4">
          <DashboardView
            summary={data.summary}
            topNudge={data.nudges[0]}
            benchmark={data.benchmark}
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
