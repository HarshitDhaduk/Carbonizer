"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import type { AuthUser } from "@/lib/types";
import { useAuthStore } from "@/store/auth-store";

/**
 * Gate an authenticated page: probes /auth/me on mount (cookies travel
 * automatically), then redirects unauthenticated visitors to onboarding.
 * Returns `ready` once the probe has resolved and the user is known.
 */
export function useAuthGuard(): { ready: boolean; user: AuthUser | null } {
  const user = useAuthStore((s) => s.user);
  const hydrated = useAuthStore((s) => s.hydrated);
  const loadMe = useAuthStore((s) => s.loadMe);
  const router = useRouter();
  const probed = useRef(false);

  useEffect(() => {
    if (probed.current) return;
    probed.current = true;
    void loadMe();
  }, [loadMe]);

  useEffect(() => {
    if (hydrated && !user) router.replace("/onboarding");
  }, [hydrated, user, router]);

  return { ready: hydrated && !!user, user };
}
