"use client";

import { useCallback, useState } from "react";
import { useAuthStore } from "@/store/auth-store";

/**
 * Shared logout-with-confirm flow used by AccountMenu (dashboard nav) and
 * ProfileClient (the explicit "Log out" button on the profile page). The two
 * call sites had identical `confirmLogout` bodies; this collapses them and
 * keeps the confirm-dialog state local to the caller.
 *
 * Returns:
 *   * `confirmOpen` / `setConfirmOpen` — drive a `ConfirmDialog`.
 *   * `requestLogout()` — opens the dialog.
 *   * `confirmLogout()` — clears the server-side session (cookies) and
 *     hard-redirects to "/". The hard nav (rather than `router.push`) avoids
 *     racing the auth-guard's redirect to /onboarding once the user clears.
 */
export function useLogoutWithConfirm() {
  const logout = useAuthStore((s) => s.logout);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const requestLogout = useCallback(() => setConfirmOpen(true), []);
  const confirmLogout = useCallback(async () => {
    await logout();
    window.location.assign("/");
  }, [logout]);

  return { confirmOpen, setConfirmOpen, requestLogout, confirmLogout };
}
