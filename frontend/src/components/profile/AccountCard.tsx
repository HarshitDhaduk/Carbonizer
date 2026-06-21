import type { AuthUser } from "@/lib/types";
import { formatCo2e } from "@/lib/format";

/**
 * Account header — the user's email, region, and personal CO₂e target.
 * Top of the Profile route.
 */
export function AccountCard({ user }: { user: AuthUser }) {
  return (
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
  );
}
