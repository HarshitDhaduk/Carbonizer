"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { AppShell } from "./AppShell";
import { AccountMenu } from "./AccountMenu";
import { useAuthGuard } from "@/lib/use-auth-guard";

/**
 * Shell for an authenticated app page: nav rail + a header (title + account menu),
 * with the auth guard handled centrally. `children` render only once authed, so
 * page content can safely fetch per-user data.
 *
 * Route-change focus management (Phase 5.1) — on every navigation we move
 * focus to the `<h1>` so screen-reader users hear the new page title rather
 * than being silently dropped on the same focus position.
 */
export function AppPage({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const { ready } = useAuthGuard();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const pathname = usePathname();

  useEffect(() => {
    headingRef.current?.focus();
  }, [pathname]);

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <h1
          ref={headingRef}
          tabIndex={-1}
          className="font-display text-xl text-text-hi focus:outline-none"
        >
          {title}
        </h1>
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
