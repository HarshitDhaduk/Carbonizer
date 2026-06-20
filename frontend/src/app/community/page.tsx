import { AppShell } from "@/components/layout/AppShell";
import { ComingSoon } from "@/components/layout/ComingSoon";
import { BenchmarkGauge } from "@/components/dashboard/BenchmarkGauge";
import { api } from "@/lib/api";

export default async function CommunityPage() {
  const benchmark = await api.getBenchmark();
  return (
    <AppShell>
      <div className="animate-fade-rise space-y-4">
        <header>
          <h1 className="font-display text-2xl text-text-hi">Community</h1>
          <p className="text-text-mid">
            See where you stand and join challenges — positively framed,
            privacy-safe.
          </p>
        </header>
        <BenchmarkGauge benchmark={benchmark} />
        <ComingSoon
          title="Challenges & achievements"
          note="Joinable challenges and biome-planting achievements are specced in docs/UI-UX-DESIGN.md §6.5."
        />
      </div>
    </AppShell>
  );
}
