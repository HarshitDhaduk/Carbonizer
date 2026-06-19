"use client";

import type { ReactNode } from "react";
import { AppShell } from "./AppShell";
import { AccountMenu } from "./AccountMenu";
import { useAuthGuard } from "@/lib/use-auth-guard";

/**
 * Shell for an authenticated app page: nav rail + a header (title + account menu),
 * with the auth guard handled centrally. `children` render only once authed, so
 * page content can safely read the token and fetch per-user data.
 */
export function AppPage({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const { ready } = useAuthGuard();

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="font-display text-xl text-text-hi">{title}</h1>
        <AccountMenu />
      </div>
      {ready ? (
        <div className="animate-fade-rise">{children}</div>
      ) : (
        <div className="skeleton h-64 rounded-card" />
      )}
    </AppShell>
  );
}
