/** Plain-JS color lerp for the SSR/2D poster (no three.js dependency). */
export function surfaceColorHex(health: number): string {
  const arid = [0x6b, 0x61, 0x49];
  const lush = [0x2f, 0x8a, 0x52];
  const t = Math.min(1, Math.max(0, health));
  const c = arid.map((a, i) => Math.round(a + (lush[i]! - a) * t));
  return `#${c.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

import type { BiomeStatus } from "@/lib/types";

const STATUS_DESCRIPTION: Record<BiomeStatus, string> = {
  seed: "just getting started — connect your data to bring it to life",
  regressing: "needs attention",
  plateau: "holding steady",
  improving: "recovering",
  thriving: "thriving",
};

/** Human-readable description for the live region / aria-label (§4.5). */
export function biomeStateLabel(status: BiomeStatus, health: number): string {
  return `Your world is ${STATUS_DESCRIPTION[status]} — ${Math.round(
    health * 100,
  )}% toward your target.`;
}
