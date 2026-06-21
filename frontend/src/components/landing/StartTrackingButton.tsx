"use client";

import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/store/auth-store";

/**
 * Landing CTA that respects returning users: signed-in visitors go straight to
 * their dashboard; everyone else starts onboarding. The decision is read at click
 * time via getState(), so it's against the latest known auth state.
 */
export function StartTrackingButton({ className }: { className?: string }) {
  const router = useRouter();

  function go() {
    const user = useAuthStore.getState().user;
    router.push(user ? "/dashboard" : "/onboarding");
  }

  return (
    <Button size="lg" onClick={go} className={className}>
      Start tracking free <ArrowRight size={18} aria-hidden />
    </Button>
  );
}
