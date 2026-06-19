import type { Config } from "tailwindcss";

/**
 * Carbonizer design tokens (see docs/UI-UX-DESIGN.md §3).
 * Colors point at CSS custom properties defined in globals.css so the
 * dark (default) / light themes swap at runtime via [data-theme].
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          base: "var(--bg-base)",
          sunken: "var(--bg-sunken)",
        },
        surface: {
          1: "var(--surface-1)",
          2: "var(--surface-2)",
          glass: "var(--surface-glass)",
        },
        border: {
          subtle: "var(--border-subtle)",
          strong: "var(--border-strong)",
        },
        brand: {
          400: "var(--brand-400)",
          500: "var(--brand-500)",
          600: "var(--brand-600)",
        },
        text: {
          hi: "var(--text-hi)",
          mid: "var(--text-mid)",
          lo: "var(--text-lo)",
        },
        cat: {
          transport: "var(--cat-transport)",
          energy: "var(--cat-energy)",
          food: "var(--cat-food)",
          spend: "var(--cat-spend)",
          home: "var(--cat-home)",
        },
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        info: "var(--info)",
      },
      borderRadius: {
        sm: "8px",
        md: "12px",
        lg: "16px",
        xl: "24px",
        card: "20px",
        pill: "999px",
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        "elev-1":
          "0 1px 0 rgba(255,255,255,.04) inset, 0 8px 24px rgba(0,0,0,.35)",
        "elev-glow": "0 0 0 1px var(--brand-glow), 0 0 32px var(--brand-glow)",
      },
      backdropBlur: {
        glass: "18px",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.16, 1, 0.3, 1)",
        inout: "cubic-bezier(0.65, 0, 0.35, 1)",
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
      transitionDuration: {
        instant: "80ms",
        fast: "160ms",
        base: "240ms",
        slow: "400ms",
        scene: "800ms",
      },
      keyframes: {
        "fade-rise": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "pop-in": {
          "0%": { opacity: "0", transform: "scale(0.9)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "fade-rise": "fade-rise 240ms cubic-bezier(0.16,1,0.3,1) both",
        "pop-in": "pop-in 400ms cubic-bezier(0.34,1.56,0.64,1) both",
      },
    },
  },
  plugins: [],
};

export default config;
