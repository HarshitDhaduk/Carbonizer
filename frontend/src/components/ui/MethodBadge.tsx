import { Check, HelpCircle, Sparkles, type LucideIcon } from "lucide-react";
import type { Method } from "@/lib/types";
import { cn } from "@/lib/cn";

/**
 * Surfaces how an emission figure was derived so users can see data quality
 * (docs/DESIGN.md §2, docs/UI-UX-DESIGN.md §6.3). Never hide the method.
 * `imputed` (R1) marks a category reconstructed from the bank "hub" — shown as
 * "Inferred" rather than the flat "Estimated".
 */
const CONFIG: Record<
  Method,
  { label: string; Icon: LucideIcon | null; glyph?: string; tone: string }
> = {
  activity: { label: "Activity-based", Icon: Check, tone: "text-success" },
  spend: { label: "Spend-based", Icon: null, glyph: "~", tone: "text-text-lo" },
  estimated: { label: "Estimated", Icon: HelpCircle, tone: "text-text-lo" },
};

const IMPUTED = { label: "Inferred", Icon: Sparkles, tone: "text-info" };

export function MethodBadge({
  method,
  imputed = false,
  className,
}: {
  method: Method;
  imputed?: boolean;
  className?: string;
}) {
  const cfg = imputed ? IMPUTED : CONFIG[method];
  const glyph = "glyph" in cfg ? cfg.glyph : undefined;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-[11px] leading-none",
        cfg.tone,
        className,
      )}
      title={
        imputed
          ? "Inferred from your bank — connect more for a measured figure"
          : `${cfg.label} measurement`
      }
    >
      {cfg.Icon ? (
        <cfg.Icon size={11} aria-hidden />
      ) : (
        <span aria-hidden className="font-mono text-[12px] leading-none">
          {glyph}
        </span>
      )}
      {cfg.label}
    </span>
  );
}
