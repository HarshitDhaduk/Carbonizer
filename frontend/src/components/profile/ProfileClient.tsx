"use client";

import { useState } from "react";
import { LogOut, ShieldCheck } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { DataConnection, Question } from "@/lib/types";
import { queries } from "@/lib/queries";
import { useAuthStore } from "@/store/auth-store";
import { visibleQuestions } from "@/lib/questionnaire";
import { formatCo2e } from "@/lib/format";
import { AppPage } from "@/components/layout/AppPage";
import { ConnectSources } from "@/components/connections/ConnectSources";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { cn } from "@/lib/cn";

export function ProfileClient() {
  return (
    <AppPage title="Profile">
      <ProfileContent />
    </AppPage>
  );
}

function ProfileContent() {
  const logout = useAuthStore((s) => s.logout);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const me = useQuery(queries.me());
  const connections = useQuery(queries.connections());
  const profile = useQuery(queries.onboardingProfile());
  const questionnaire = useQuery(queries.onboardingQuestions());

  const isLoading =
    me.isPending ||
    connections.isPending ||
    profile.isPending ||
    questionnaire.isPending;
  const error =
    me.error ?? connections.error ?? profile.error ?? questionnaire.error;

  async function confirmLogout() {
    await logout();
    window.location.assign("/");
  }

  if (error)
    return (
      <p className="text-sm text-danger">Couldn&apos;t load your profile.</p>
    );
  if (
    isLoading ||
    !me.data ||
    !connections.data ||
    !profile.data ||
    !questionnaire.data
  )
    return <div className="skeleton h-64 rounded-card" />;

  const user = me.data;
  const answers = profile.data.answers ?? {};
  const questions = questionnaire.data.questions;

  return (
    <div className="space-y-4">
      {/* account */}
      <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
        <div className="flex items-center gap-3">
          <span className="bg-brand-500/20 grid h-11 w-11 place-items-center rounded-full text-base font-medium text-brand-400">
            {user.email.charAt(0).toUpperCase()}
          </span>
          <div className="min-w-0">
            <p className="truncate font-medium text-text-hi">{user.email}</p>
            <p className="text-sm text-text-mid">
              {user.region}
              {user.targetTco2e != null && (
                <> · target {formatCo2e(user.targetTco2e)}/yr</>
              )}
            </p>
          </div>
        </div>
      </section>

      {/* data sources */}
      <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
        <h2 className="mb-3 text-sm font-medium text-text-mid">Your data</h2>
        <ul className="mb-3 space-y-2">
          {connections.data.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-text-hi">{c.label}</span>
              <ConnectionStatus status={c.status} lastSync={c.lastSync} />
            </li>
          ))}
        </ul>
        <ConnectSources onSummary={() => {}} />
      </section>

      {/* onboarding answers */}
      {profile.data.answers && (
        <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
          <h2 className="mb-3 text-sm font-medium text-text-mid">
            Your starting profile
          </h2>
          <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {visibleQuestions(questions, answers).map((q) => (
              <div
                key={q.id}
                className="flex items-center justify-between gap-3 rounded-md bg-surface-2 px-3 py-2 text-sm"
              >
                <dt className="text-text-mid">{q.label}</dt>
                <dd className="text-right text-text-hi">
                  {renderAnswer(q, answers[q.id])}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {/* privacy */}
      <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-medium text-text-mid">
          <ShieldCheck size={15} aria-hidden className="text-brand-400" />
          Privacy &amp; control
        </h2>
        <p className="text-sm text-text-mid">
          Your data is used only to calculate your footprint — never sold or
          used for advertising. You can disconnect any source above, and request
          a full export or erasure at any time (GDPR &amp; DPDP).
        </p>
      </section>

      {/* sign out */}
      <Button
        variant="danger"
        className="w-full"
        onClick={() => setConfirmOpen(true)}
      >
        <LogOut size={16} aria-hidden /> Log out
      </Button>

      <ConfirmDialog
        open={confirmOpen}
        title="Log out of Carbonizer?"
        description="You'll need to sign in again to see your dashboard."
        confirmLabel="Log out"
        confirmVariant="danger"
        onConfirm={confirmLogout}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}

function ConnectionStatus({
  status,
  lastSync,
}: {
  status: DataConnection["status"];
  lastSync: string | undefined;
}) {
  const connected = status === "connected";
  const attention = status === "needs-attention";
  const label = connected
    ? (lastSync ?? "Connected")
    : attention
      ? "Needs attention"
      : "Not connected";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs",
        connected
          ? "text-brand-400"
          : attention
            ? "text-warning"
            : "text-text-lo",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          connected ? "bg-brand-400" : attention ? "bg-warning" : "bg-text-lo",
        )}
      />
      {label}
    </span>
  );
}

function renderAnswer(q: Question, value: unknown): string {
  if (q.type === "single") {
    const opt = q.options?.find((o) => o.value === value);
    return opt?.label ?? String(value ?? "—");
  }
  return `${value ?? "—"}${q.unit ? ` ${q.unit}` : ""}`;
}
