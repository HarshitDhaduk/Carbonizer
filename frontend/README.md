# Carbonizer — Frontend

Next.js (App Router) + TypeScript + Tailwind + React Three Fiber. Implements the
dark-first "premium fintech-meets-nature" design system and the Living Planet 3D
biome from [`../docs/UI-UX-DESIGN.md`](../docs/UI-UX-DESIGN.md).

## Quick start

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000  → redirects to /dashboard
```

Other scripts:

```bash
npm run build        # production build
npm run typecheck    # tsc --noEmit (strict)
npm run lint         # next lint
```

## Backend (FastAPI)

The UI runs on mock data out of the box. To point it at the Python FastAPI
backend, set the API origin and the client in `src/lib/api.ts` will call the
live endpoints (contract in docs/UI-UX-DESIGN.md §13):

```bash
# frontend/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

When `NEXT_PUBLIC_API_BASE_URL` is empty, every call resolves to the fixtures in
`src/lib/mock-data.ts`.

## Structure

```
src/
  app/                     # App Router routes
    layout.tsx             # fonts, theme, metadata
    globals.css            # design tokens (CSS vars) + base styles
    page.tsx               # → redirects to /dashboard
    dashboard/page.tsx     # the home screen (server) + DashboardView (client)
    insights|act|community|profile/   # placeholder routes (specced, not built)
  components/
    biome/                 # Living Planet: Scene (R3F), Planet, Poster, Canvas
    dashboard/             # FootprintPill, StatCard, NudgeCard, BenchmarkGauge …
    layout/                # NavRail, MobileTabBar, AppShell, Logo
    ui/                    # Button, MethodBadge, TrendDelta, Sparkline
  lib/                     # types, tokens, formatters, api client, mock data
  store/                   # zustand biome store (shared by 3D + cards)
```

## Design-system notes

- **Tokens** live as CSS custom properties in `globals.css` (dark + light) and are
  surfaced to Tailwind in `tailwind.config.ts`. Theme swaps via `data-theme`.
- **The biome** (`components/biome`) runs `frameloop="demand"` and lazy-loads the
  WebGL scene behind a static poster — both for performance and the project's
  "Green AI" budget (docs §4.4). It always has a 2D / reduced-motion fallback
  (docs §4.5).
- **Accessibility:** trends/categories never rely on color alone; the canvas is
  `role="img"` with a live text description; honors `prefers-reduced-motion`.
