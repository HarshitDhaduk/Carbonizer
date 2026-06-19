import { cn } from "@/lib/cn";

/**
 * Wordmark with the planet "O" motif (docs/UI-UX-DESIGN.md §2). The ringed
 * planet stands in for the brand's living-world centerpiece.
 */
export function Logo({
  showWordmark = true,
  className,
}: {
  showWordmark?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <svg
        width={26}
        height={26}
        viewBox="0 0 26 26"
        fill="none"
        aria-hidden
        className="shrink-0"
      >
        <circle cx="13" cy="13" r="7.5" fill="var(--brand-500)" />
        <ellipse
          cx="13"
          cy="13"
          rx="11"
          ry="4"
          fill="none"
          stroke="var(--brand-400)"
          strokeWidth="1.5"
          opacity="0.7"
          transform="rotate(-20 13 13)"
        />
      </svg>
      {showWordmark && (
        <span className="font-display text-base font-medium text-text-hi">
          Carbonizer
        </span>
      )}
    </span>
  );
}
