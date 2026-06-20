"use client";

import { useState } from "react";
import { LogOut } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { cn } from "@/lib/cn";

/** Compact account chip with a logout menu (confirmed via a modal). */
export function AccountMenu({ className }: { className?: string }) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [open, setOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const email = user?.email ?? "Account";
  const initial = email.charAt(0).toUpperCase();

  function confirmLogout() {
    logout();
    // hard navigation to the landing page — avoids the dashboard auth-guard
    // racing us to /onboarding when the token clears, and fully resets state.
    window.location.assign("/");
  }

  return (
    <div className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-pill border border-border-subtle bg-surface-1 py-1 pl-1 pr-3 text-sm text-text-mid transition-colors hover:text-text-hi"
      >
        <span
          aria-hidden
          className="bg-brand-500/20 grid h-7 w-7 place-items-center rounded-full text-xs font-medium text-brand-400"
        >
          {initial}
        </span>
        <span className="hidden max-w-[160px] truncate sm:inline">{email}</span>
      </button>

      {open && (
        <>
          {/* click-away backdrop */}
          <button
            type="button"
            aria-hidden
            tabIndex={-1}
            className="fixed inset-0 z-10 cursor-default"
            onClick={() => setOpen(false)}
          />
          <div
            role="menu"
            className="glass absolute right-0 z-20 mt-2 w-56 rounded-md border border-border-subtle p-1.5 shadow-elev-1"
          >
            <p className="truncate px-2.5 py-1.5 text-xs text-text-lo">
              {email}
            </p>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                setConfirmOpen(true);
              }}
              className="flex w-full items-center gap-2 rounded-sm px-2.5 py-2 text-left text-sm text-text-hi transition-colors hover:bg-surface-2"
            >
              <LogOut size={15} aria-hidden />
              Log out
            </button>
          </div>
        </>
      )}

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
