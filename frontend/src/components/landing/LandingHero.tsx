"use client";

import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { BiomeCanvas } from "@/components/biome/BiomeCanvas";
import { StartTrackingButton } from "./StartTrackingButton";

/**
 * Landing hero (docs/UI-UX-DESIGN.md §2/§6.1). The auto-rotating Living Planet
 * is the emotional hook; the copy promises automation + reduction, not guilt.
 */
export function LandingHero() {
  return (
    <section className="relative overflow-hidden">
      {/* ambient brand glow */}
      <div
        aria-hidden
        className="bg-brand-500/15 pointer-events-none absolute left-1/2 top-[-10%] h-[520px] w-[520px] -translate-x-1/2 rounded-full blur-[120px]"
      />

      <div className="mx-auto grid max-w-6xl items-center gap-8 px-4 pb-12 pt-10 md:grid-cols-2 md:px-6 md:pb-20 md:pt-16">
        <div className="animate-fade-rise">
          <span className="inline-flex items-center gap-2 rounded-pill border border-border-subtle bg-surface-1 px-3 py-1 text-xs text-text-mid">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-400" />
            Automated carbon tracking — no manual logging
          </span>

          <h1 className="mt-5 font-display text-4xl leading-[1.05] text-text-hi md:text-6xl">
            Watch your world{" "}
            <span className="text-brand-400">come back to life.</span>
          </h1>

          <p className="mt-5 max-w-md text-lg text-text-mid">
            Carbonizer turns your everyday spending, travel and energy use into
            a living planet — then shows you the few changes that shrink your
            footprint and your bills.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <StartTrackingButton />
            <a href="#how">
              <Button size="lg" variant="secondary">
                See how it works
              </Button>
            </a>
          </div>

          <p className="mt-6 flex items-center gap-2 text-sm text-text-lo">
            <ShieldCheck size={15} aria-hidden className="text-brand-400" />
            Bank-grade encryption · GDPR &amp; DPDP compliant · You control your
            data
          </p>
        </div>

        {/* the showpiece */}
        <div className="relative h-[360px] md:h-[520px]">
          <BiomeCanvas
            variant="hero"
            health={0.82}
            status="thriving"
            caption="Tap to plant · drag to orbit"
          />
        </div>
      </div>
    </section>
  );
}
