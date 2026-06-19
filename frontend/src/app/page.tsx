import { LandingNav } from "@/components/landing/LandingNav";
import { LandingHero } from "@/components/landing/LandingHero";
import { FeatureSections } from "@/components/landing/FeatureSections";
import { LandingFooter } from "@/components/landing/LandingFooter";

export default function LandingPage() {
  return (
    <div className="min-h-dvh bg-bg-base">
      <LandingNav />
      <main>
        <LandingHero />
        <FeatureSections />
      </main>
      <LandingFooter />
    </div>
  );
}
