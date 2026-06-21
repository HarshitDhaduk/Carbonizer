import type { DataConnection } from "@/lib/types";
import { cn } from "@/lib/cn";

/**
 * Visual + textual status for a single Connection row — "connected · 2h ago",
 * "Needs attention", or "Not connected" — colour-coded with a dot indicator.
 */
export function ConnectionStatusBadge({
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
