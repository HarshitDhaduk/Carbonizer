"use client";

import { useState } from "react";
import { Building2, Check, Zap, type LucideIcon } from "lucide-react";
import type { ConnectProvider, FootprintSummary } from "@/lib/types";
import { ApiError, clientApi } from "@/lib/client-api";
import { useAuthStore } from "@/store/auth-store";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

interface Source {
  id: ConnectProvider;
  label: string;
  blurb: string;
  Icon: LucideIcon;
  /** what connecting upgrades the data to */
  upgrade: string;
}

const SOURCES: Source[] = [
  {
    id: "bank",
    label: "Your bank",
    blurb: "Replace estimates with real spending.",
    Icon: Building2,
    upgrade: "spend-based",
  },
  {
    id: "meter",
    label: "Home energy",
    blurb: "Use metered kWh and the live grid mix.",
    Icon: Zap,
    upgrade: "activity-based",
  },
];

/**
 * Connect data sources to upgrade footprint accuracy (Progressive Data Depth).
 * Each successful connect hands the recomputed summary back via `onSummary`.
 */
export function ConnectSources({
  onSummary,
  className,
}: {
  onSummary: (summary: FootprintSummary) => void;
  className?: string;
}) {
  const token = useAuthStore((s) => s.token);
  const [busy, setBusy] = useState<ConnectProvider | null>(null);
  const [done, setDone] = useState<Partial<Record<ConnectProvider, number>>>({});
  const [error, setError] = useState<string | null>(null);

  async function connect(provider: ConnectProvider) {
    if (!token) return;
    setBusy(provider);
    setError(null);
    try {
      const res = await clientApi.linkSource(token, provider);
      onSummary(res.summary);
      setDone((d) => ({ ...d, [provider]: res.recordsImported }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't connect — try again.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={cn("space-y-2", className)}>
      {SOURCES.map((s) => {
        const records = done[s.id];
        const connected = records !== undefined;
        return (
          <div
            key={s.id}
            className="flex items-center justify-between gap-4 rounded-md border border-border-subtle bg-surface-1 p-3.5"
          >
            <div className="flex min-w-0 items-start gap-3">
              <span
                className={cn(
                  "grid h-9 w-9 shrink-0 place-items-center rounded-md",
                  connected
                    ? "bg-brand-500/15 text-brand-400"
                    : "bg-surface-2 text-text-mid",
                )}
              >
                {connected ? <Check size={18} aria-hidden /> : <s.Icon size={18} aria-hidden />}
              </span>
              <div className="min-w-0 text-sm">
                <p className="font-medium text-text-hi">{s.label}</p>
                <p className="text-text-mid">
                  {connected ? (
                    <>
                      Imported {records} records · now{" "}
                      <span className="text-brand-400">{s.upgrade}</span>
                    </>
                  ) : (
                    <>
                      {s.blurb}{" "}
                      <span className="text-text-lo">Read-only · demo</span>
                    </>
                  )}
                </p>
              </div>
            </div>
            {!connected && (
              <Button
                size="sm"
                variant="secondary"
                className="shrink-0"
                onClick={() => connect(s.id)}
                disabled={busy !== null}
              >
                {busy === s.id ? "Connecting…" : "Connect"}
              </Button>
            )}
          </div>
        );
      })}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
