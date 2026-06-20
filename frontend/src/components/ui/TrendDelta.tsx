import {
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  type LucideIcon,
} from "lucide-react";
import type { Trend } from "@/lib/types";
import { formatPct } from "@/lib/format";
import { cn } from "@/lib/cn";

/**
 * Trend never relies on color alone — always paired with an arrow/icon and a
 * percent label (docs/UI-UX-DESIGN.md §11, color independence).
 * For emissions, "down" is good → success tone.
 */
const CONFIG: Record<Trend, { Icon: LucideIcon; tone: string; sr: string }> = {
  down: { Icon: ArrowDownRight, tone: "text-success", sr: "down" },
  up: { Icon: ArrowUpRight, tone: "text-danger", sr: "up" },
  flat: { Icon: Minus, tone: "text-text-lo", sr: "unchanged" },
};

export function TrendDelta({
  trend,
  deltaPct,
  className,
  suffix,
}: {
  trend: Trend;
  deltaPct: number;
  className?: string;
  suffix?: string;
}) {
  const { Icon, tone, sr } = CONFIG[trend];
  return (
    <span
      className={cn(
        "tnum inline-flex items-center gap-1 text-sm",
        tone,
        className,
      )}
    >
      <Icon size={14} aria-hidden />
      <span>
        {trend === "flat" ? "flat" : formatPct(deltaPct)}
        {suffix ? ` ${suffix}` : ""}
      </span>
      <span className="sr-only">{sr} versus previous period</span>
    </span>
  );
}
