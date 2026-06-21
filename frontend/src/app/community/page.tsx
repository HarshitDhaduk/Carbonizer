import { AppShell } from "@/components/layout/AppShell";
import { ComingSoon } from "@/components/layout/ComingSoon";
import { BenchmarkGauge } from "@/components/dashboard/BenchmarkGauge";
import { MOCK_BENCHMARK } from "@/lib/mock-data";

// The Community page is a "coming soon" surface — the real benchmark gauge
// renders against a fixture so the SSR'd shell doesn't need an authenticated
// session round-trip. The fully-wired benchmark (with R4 IPW + Laplace DP)
// is on /insights once the user is signed in.
export default function CommunityPage() {
  const benchmark = MOCK_BENCHMARK;
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
