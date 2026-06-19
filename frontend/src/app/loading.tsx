import { AppShell } from "@/components/layout/AppShell";

/** Branded skeleton shown while route data resolves (docs §8). */
export default function Loading() {
  return (
    <AppShell>
      <div className="space-y-4">
        <div className="skeleton h-14 rounded-lg" />
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="skeleton h-[340px] rounded-card" />
          <div className="grid grid-cols-2 gap-2.5">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="skeleton h-28 rounded-md" />
            ))}
          </div>
        </div>
        <div className="skeleton h-20 rounded-lg" />
        <div className="skeleton h-24 rounded-lg" />
      </div>
    </AppShell>
  );
}
