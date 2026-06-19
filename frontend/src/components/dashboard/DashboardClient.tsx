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
 * The authenticated, per-user dashboard. Fetches the current user's own footprint
 * client-side with their token (the public SSR route is gone) and guards access —
 * unauthenticated visitors are sent to onboarding.
 */
export function DashboardClient() {
  const token = useAuthStore((s) => s.token);
  const loadMe = useAuthStore((s) => s.loadMe);
  const router = useRouter();

  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Wait for zustand-persist to rehydrate the token from localStorage before
  // deciding anything — otherwise the first render sees null and wrongly
  // redirects a signed-in user to onboarding.
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    setHydrated(useAuthStore.persist.hasHydrated());
    return useAuthStore.persist.onFinishHydration(() => setHydrated(true));
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.replace("/onboarding");
      return;
    }
    void loadMe();
    let active = true;
    Promise.all([
      clientApi.getFootprintSummary(token),
      clientApi.getRecommendations(token),
      clientApi.getBenchmark(token),
    ])
      .then(([summary, nudges, benchmark]) => {
        if (active) setData({ summary, nudges, benchmark });
      })
      .catch((e) => {
        if (!active) return;
        if (e instanceof ApiError && e.status === 401) {
          useAuthStore.getState().logout();
          router.replace("/onboarding");
          return;
        }
        setError(e instanceof Error ? e.message : "Couldn't load your dashboard.");
      });
    return () => {
      active = false;
    };
  }, [hydrated, token, loadMe, router]);

  function onConnected(summary: FootprintSummary) {
    setData((d) => (d ? { ...d, summary } : d));
  }

  if (!hydrated)
    return (
      <AppShell>
        <DashboardSkeleton />
      </AppShell>
    );
  if (!token) return null; // redirecting

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
