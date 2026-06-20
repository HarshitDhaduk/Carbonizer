import { surfaceColorHex } from "./poster-helpers";

/**
 * Static, accessible representation of the biome. Used as:
 *  - the loading poster before the WebGL scene hydrates,
 *  - the permanent fallback under prefers-reduced-motion or "2D mode" (§4.5).
 * Carries no motion. The textual state lives in BiomeCanvas' live region.
 */
export function BiomePoster({ health }: { health: number }) {
  const fill = surfaceColorHex(health);
  const treeCount = Math.max(3, Math.round(10 * health));

  return (
    <svg viewBox="0 0 240 240" className="h-full w-full" role="img" aria-hidden>
      <ellipse
        cx="120"
        cy="120"
        rx="112"
        ry="38"
        fill="none"
        stroke="var(--brand-400)"
        strokeWidth="1.5"
        opacity="0.3"
        transform="rotate(-18 120 120)"
      />
      <circle cx="120" cy="120" r="78" fill={fill} />
      <circle
        cx="120"
        cy="120"
        r="78"
        fill="none"
        stroke="var(--brand-600)"
        strokeWidth="1.5"
        opacity="0.5"
      />
      {Array.from({ length: treeCount }).map((_, i) => {
        const angle = (i / treeCount) * Math.PI * 2;
        const r = 40 + (i % 3) * 12;
        const x = 120 + Math.cos(angle) * r;
        const y = 120 + Math.sin(angle) * r * 0.8;
        const s = 7 + (i % 4);
        return <circle key={i} cx={x} cy={y} r={s} fill="var(--brand-500)" />;
      })}
    </svg>
  );
}
