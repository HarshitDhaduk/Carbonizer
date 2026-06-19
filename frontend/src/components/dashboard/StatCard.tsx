"use client";

import { Bolt, Car, ShoppingBag, Salad, Home, type LucideIcon } from "lucide-react";
import type { CategoryBreakdown, Category } from "@/lib/types";
import { CATEGORY_HEX, CATEGORY_LABEL } from "@/lib/tokens";
import { formatCo2e } from "@/lib/format";
import { TrendDelta } from "@/components/ui/TrendDelta";
import { MethodBadge } from "@/components/ui/MethodBadge";
import { Sparkline } from "@/components/ui/Sparkline";
import { useBiomeStore } from "@/store/biome-store";
import { cn } from "@/lib/cn";

const ICON: Record<Category, LucideIcon> = {
  transport: Car,
  energy: Bolt,
  food: Salad,
  spend: ShoppingBag,
  home: Home,
};

/**
 * Category metric card. Clicking selects the matching biome region
 * (cross-highlight) and drills into Insights (docs/UI-UX-DESIGN.md §6.2/§4.3).
 */
export function StatCard({ data }: { data: CategoryBreakdown }) {
  const Icon = ICON[data.category];
  const color = CATEGORY_HEX[data.category];
  const selected = useBiomeStore((s) => s.selectedCategory === data.category);
  const select = useBiomeStore((s) => s.setSelectedCategory);

  return (
    <button
      type="button"
      onClick={() => select(selected ? null : data.category)}
      aria-pressed={selected}
      className={cn(
        "group flex flex-col rounded-md border bg-surface-1 p-3 text-left transition-colors duration-fast",
        "hover:bg-surface-2",
        selected ? "border-brand-500/60" : "border-border-subtle",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-xs text-text-lo">
          <Icon size={14} aria-hidden style={{ color }} />
          {CATEGORY_LABEL[data.category]}
        </span>
        <Sparkline data={data.spark} color={color} />
      </div>

      <p className="mt-1.5 font-display text-lg text-text-hi tnum leading-none">
        {formatCo2e(data.tco2e)}
      </p>

      <div className="mt-1.5 flex items-center justify-between">
        <TrendDelta trend={data.trend} deltaPct={data.deltaPct} />
        <MethodBadge method={data.method} imputed={data.imputed ?? false} />
      </div>
    </button>
  );
}
