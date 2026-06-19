"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/store/auth-store";

/**
 * Landing nav CTA — "Open dashboard" for a signed-in user, "Open app" otherwise.
 * `mounted` gates on client hydration so the label never mismatches the SSR markup
 * (server + first client render show "Open app", then it updates if logged in).
 */
export function OpenAppButton() {
  const token = useAuthStore((s) => s.token);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const loggedIn = mounted && !!token;

  return (
    <Link href="/dashboard">
      <Button size="sm">
        {loggedIn ? "Open dashboard" : "Open app"}{" "}
        <ArrowRight size={15} aria-hidden />
      </Button>
    </Link>
  );
}
