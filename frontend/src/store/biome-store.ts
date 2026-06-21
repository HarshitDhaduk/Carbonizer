import { create } from "zustand";
import type { BiomeStatus, Category, FootprintSummary } from "@/lib/types";

/**
 * Single source of truth shared by the 3D biome and the dashboard cards
 * (docs/UI-UX-DESIGN.md §12). The scene subscribes to `health` and
 * `categoryIntensity`; the UI writes them from the footprint summary.
 */

/** A user-planted tree, stored as a unit-sphere direction [x,y,z]. */
export type PlantPoint = [number, number, number];

const MAX_PLANTED = 140;

export interface BiomeState {
  /** 0..1 — drives global lushness of the planet. */
  health: number;
  status: BiomeStatus;
  /** 0..1 per category — drives region density (roads, grid, farmland…). */
  categoryIntensity: Record<Category, number>;
  /** transient flag that fires a celebration burst (tree-plant + confetti). */
  celebrating: boolean;
  /** which region the user last selected, for cross-highlighting with cards. */
  selectedCategory: Category | null;
  /** trees the user has planted by tapping the planet. */
  plantedPoints: PlantPoint[];

  hydrateFromSummary: (summary: FootprintSummary) => void;
  setSelectedCategory: (c: Category | null) => void;
  celebrate: () => void;
  endCelebration: () => void;
  plantTree: (p: PlantPoint) => void;
  /** Plant a tree at a random unit-sphere direction — used by the keyboard /
   * pointer-less "Plant a tree" button (Phase 5.2 of docs/IMPROVEMENT-PLAN.md). */
  plantRandom: () => void;
  resetPlanting: () => void;
}

const DEFAULT_INTENSITY: Record<Category, number> = {
  transport: 0.5,
  energy: 0.5,
  food: 0.5,
  spend: 0.5,
  home: 0.5,
};

/** Normalize a category's tCO2e into a 0..1 intensity (cap at ~2.5 t). */
function intensity(tco2e: number): number {
  return Math.min(1, Math.max(0, tco2e / 2.5));
}

export const useBiomeStore = create<BiomeState>((set) => ({
  health: 0.5,
  status: "plateau",
  categoryIntensity: DEFAULT_INTENSITY,
  celebrating: false,
  selectedCategory: null,
  plantedPoints: [],

  hydrateFromSummary: (summary) =>
    set(() => {
      const categoryIntensity = { ...DEFAULT_INTENSITY };
      for (const c of summary.categories) {
        categoryIntensity[c.category] = intensity(c.tco2e);
      }
      return {
        health: summary.health,
        status: summary.status,
        categoryIntensity,
      };
    }),

  setSelectedCategory: (selectedCategory) => set({ selectedCategory }),
  celebrate: () => set({ celebrating: true }),
  endCelebration: () => set({ celebrating: false }),

  plantTree: (p) =>
    set((s) => ({
      // newest LAST (the Forest pops the final index); cap from the end so a
      // freshly planted tree is never the one dropped at the budget ceiling.
      plantedPoints: [...s.plantedPoints, p].slice(-MAX_PLANTED),
      celebrating: true,
    })),

  plantRandom: () => {
    // Uniformly distributed point on the unit sphere via Marsaglia's method.
    // Existing planted points already follow the canvas-tap distribution; this
    // mirrors that without any pointer dependency.
    let x = 0;
    let y = 0;
    let s = 2;
    while (s >= 1) {
      x = Math.random() * 2 - 1;
      y = Math.random() * 2 - 1;
      s = x * x + y * y;
    }
    const factor = 2 * Math.sqrt(1 - s);
    set((state) => ({
      plantedPoints: [
        ...state.plantedPoints,
        [x * factor, y * factor, 1 - 2 * s] as PlantPoint,
      ].slice(-MAX_PLANTED),
      celebrating: true,
    }));
  },

  resetPlanting: () => set({ plantedPoints: [] }),
}));
