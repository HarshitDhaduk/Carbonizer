"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
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
  const plantRandom = useBiomeStore((s) => s.plantRandom);

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

  // Defer the three.js mount until the main thread is idle so first-paint
  // + LCP land on the cheap poster alone. Cuts Total Blocking Time on the
  // landing route from ~1 s to roughly the cost of the static hero — three.js
  // initialisation moves *after* the user can interact (Phase 4.5).
  const [idle, setIdle] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const w = window as Window &
      typeof globalThis & {
        requestIdleCallback?: (
          cb: () => void,
          opts?: { timeout: number },
        ) => number;
        cancelIdleCallback?: (id: number) => void;
      };
    if (w.requestIdleCallback) {
      const id = w.requestIdleCallback(() => setIdle(true), { timeout: 1500 });
      return () => w.cancelIdleCallback?.(id);
    }
    const id = window.setTimeout(() => setIdle(true), 600);
    return () => window.clearTimeout(id);
  }, []);

  const live3d = !use2D && onScreen && idle;

  /** Pointer-less plant: keyboard users (Space / Enter on the focused canvas
   * or the explicit button) get the same affordance as a tap. Camera orbit by
   * keyboard is a tracked Phase 5.2 follow-up (needs an OrbitControls ref
   * plumbed through the dynamically-loaded scene). */
  function onCanvasKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (use2D) return;
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      plantRandom();
    }
  }

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
        className="relative aspect-square w-full max-w-[420px] rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-400"
        role={use2D ? "img" : "application"}
        aria-label={
          use2D
            ? label
            : `${label}. Press Space or Enter to plant a tree. Tap or drag for pointer controls.`
        }
        tabIndex={use2D ? undefined : 0}
        onKeyDown={onCanvasKeyDown}
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

      {/* Pointer-less planting affordance (Phase 5.2). Mirrors the canvas-tap
          action for keyboard / switch / SR users; lives outside the canvas
          stack so it's reachable by Tab order regardless of focus state. */}
      {!use2D && (
        <button
          type="button"
          onClick={plantRandom}
          className="mt-2 inline-flex items-center gap-1.5 rounded-pill border border-border-subtle bg-surface-1 px-3 py-1.5 text-xs font-medium text-text-hi transition-colors hover:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-400"
        >
          <Sprout size={13} aria-hidden className="text-brand-400" />
          Plant a tree
        </button>
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
