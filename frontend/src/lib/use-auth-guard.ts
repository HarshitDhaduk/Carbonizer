"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";

/**
 * Gate an authenticated page: waits for zustand-persist to rehydrate the token,
 * then redirects signed-out visitors to onboarding. Returns `ready` once we have
 * a confirmed token so the page can fetch its data.
 */
export function useAuthGuard(): { ready: boolean; token: string | null } {
  const token = useAuthStore((s) => s.token);
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(useAuthStore.persist.hasHydrated());
    return useAuthStore.persist.onFinishHydration(() => setHydrated(true));
  }, []);

  useEffect(() => {
    if (hydrated && !token) router.replace("/onboarding");
  }, [hydrated, token, router]);

  return { ready: hydrated && !!token, token: hydrated ? token : null };
}
