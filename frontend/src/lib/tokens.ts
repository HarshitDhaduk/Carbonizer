import type { Category } from "./types";

/**
 * Runtime-readable design tokens for non-CSS consumers (the Three.js scene,
 * canvas charts). Keep in sync with globals.css. Values are the dark-theme
 * defaults; the biome reads live CSS vars where possible (see readCssVar).
 */

export const CATEGORY_HEX: Record<Category, string> = {
  transport: "#38bdf8",
  energy: "#fbbf24",
  food: "#a3e635",
  spend: "#c084fc",
  home: "#fb923c",
};

export const CATEGORY_LABEL: Record<Category, string> = {
  transport: "Transport",
  energy: "Energy",
  food: "Food",
  spend: "Spend",
  home: "Home",
};

export const BRAND = {
  green: "#2bd576",
  greenBright: "#4fe08c",
  greenDeep: "#1fae5e",
};

/** Read a CSS custom property at runtime (client only). Falls back to `fallback`. */
export function readCssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return v || fallback;
}
