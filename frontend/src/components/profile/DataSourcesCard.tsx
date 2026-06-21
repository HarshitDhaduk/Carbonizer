import type { DataConnection } from "@/lib/types";
import { ConnectSources } from "@/components/connections/ConnectSources";
import { ConnectionStatusBadge } from "./ConnectionStatusBadge";

/**
 * "Your data" section on the Profile route — shows the three providers and
 * their connection state, plus the buttons to connect a sandbox source.
 */
export function DataSourcesCard({
  connections,
}: {
  connections: DataConnection[];
}) {
  return (
    <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
      <h2 className="mb-3 text-sm font-medium text-text-mid">Your data</h2>
      <ul className="mb-3 space-y-2">
        {connections.map((c) => (
          <li key={c.id} className="flex items-center justify-between text-sm">
            <span className="text-text-hi">{c.label}</span>
            <ConnectionStatusBadge status={c.status} lastSync={c.lastSync} />
          </li>
        ))}
      </ul>
      <ConnectSources onSummary={() => {}} />
    </section>
  );
}
