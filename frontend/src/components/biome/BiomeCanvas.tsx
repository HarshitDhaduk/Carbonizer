"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { Move3d, Sprout, RotateCcw } from "lucide-react";
import type { BiomeStatus } from "@/lib/types";
import { useReducedMotion } from "@/lib/use-reduced-motion";
import { useBiomeStore } from "@/store/biome-store";
import { BiomePoster } from "./BiomePoster";
import { biomeStateLabel } from "./poster-helpers";

// Lazy-load the WebGL scene (client only) behind the static poster so first
// paint and Lighthouse aren't penalized (docs/UI-UX-DESIGN.md §4.4).
const BiomeScene = dynamic(() => import("./BiomeScene"), {
  ssr: false,
  loading: () => null,
});

export function BiomeCanvas({
  health,
  status,
  caption,
  variant = "dashboard",
  /** force the 2D poster (the Settings "2D mode" toggle, §4.5). */
  force2D = false,
}: {
  health: number;
  status: BiomeStatus;
  caption?: string;
  variant?: "dashboard" | "hero";
  force2D?: boolean;
}) {
  const reducedMotion = useReducedMotion();
  const use2D = force2D || reducedMotion;
  const label = biomeStateLabel(status, health);

  const planted = useBiomeStore((s) => s.plantedPoints.length);
  const resetPlanting = useBiomeStore((s) => s.resetPlanting);

  // Only mount the WebGL scene while it's actually on screen — fully releasing
  // the GPU when scrolled away (honest "pause when offscreen", §4.4).
  const wrapRef = useRef<HTMLDivElement>(null);
  const [onScreen, setOnScreen] = useState(false);
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => setOnScreen(entry?.isIntersecting ?? false),
      { rootMargin: "100px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const live3d = !use2D && onScreen;

  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center">
      <div className="pointer-events-none absolute left-3 top-3 z-10 flex items-center gap-1.5 text-xs text-text-lo">
        <Move3d size={14} aria-hidden />
        {use2D
          ? "Your living world"
          : "Tap the planet to plant · drag to orbit"}
      </div>

      <div
        ref={wrapRef}
        className="relative aspect-square w-full max-w-[420px]"
        role="img"
        aria-label={label}
      >
        {use2D ? (
          <BiomePoster health={health} />
        ) : (
          <>
            {/* poster paints instantly; the scene fades in over it */}
            <div className="absolute inset-0">
              <BiomePoster health={health} />
            </div>
            {live3d && (
              <div className="absolute inset-0 animate-fade-rise">
                <BiomeScene
                  variant={variant}
                  {...(variant === "hero" ? { healthOverride: health } : {})}
                />
              </div>
            )}
          </>
        )}
      </div>

      {/* planting HUD */}
      {!use2D && (
        <div className="pointer-events-none absolute bottom-2 right-3 z-10 flex items-center gap-2">
          <span className="tnum pointer-events-none inline-flex items-center gap-1.5 rounded-pill bg-surface-glass px-2.5 py-1 text-xs text-text-mid backdrop-blur">
            <Sprout size={13} aria-hidden className="text-brand-400" />
            {planted} planted
          </span>
          {planted > 0 && (
            <button
              type="button"
              onClick={resetPlanting}
              className="pointer-events-auto inline-flex items-center gap-1 rounded-pill bg-surface-2 px-2 py-1 text-xs text-text-lo transition-colors hover:text-text-hi"
              aria-label="Clear planted trees"
            >
              <RotateCcw size={12} aria-hidden />
            </button>
          )}
        </div>
      )}

      {/* polite live region announces significant state changes */}
      <p className="sr-only" aria-live="polite">
        {label}
      </p>

      <div className="mt-1 text-center">
        <p className="font-medium capitalize text-text-hi">
          {status === "improving" ? "Recovering" : status}
        </p>
        {caption && <p className="text-sm text-text-mid">{caption}</p>}
      </div>
    </div>
  );
}
