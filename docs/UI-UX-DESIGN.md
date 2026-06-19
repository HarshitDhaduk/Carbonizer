# Carbonizer — UI/UX Design Specification

> Visual, interaction, and design-system spec for the Carbonizer web app.
> **Stack:** Next.js (App Router) + React Three Fiber/Three.js on the frontend,
> Python FastAPI on the backend. Companion to [DESIGN.md](DESIGN.md).

**Direction (locked):**
- **Signature 3D experience:** *Living Planet / Biome* — a personal world that heals or
  degrades with the user's footprint.
- **Visual tone:** *Premium fintech-meets-nature* — dark-first, deep greens, glassmorphism,
  precise data viz, restrained motion.
- **Scope:** Full app (onboarding, dashboard, insights, recommendations, social, settings).

---

## 1. Design Philosophy

Carbonizer must feel **as trustworthy as a banking app and as alive as a game**. It holds
the user's financial, location, and home-energy data, so the interface must signal
security and precision — while the 3D biome makes an abstract metric (CO₂e) viscerally
personal.

### Five Product-Specific Design Principles

1. **Show the world, not the number first.** The hero is the living planet; the metric is
   its caption. We lead with consequence, then detail (System 1 → System 2).
2. **Automated, ambient, low-effort.** Because data flows in automatically, the default
   posture is *glanceable*. Deep analysis is opt-in, never required.
3. **Every screen answers "so what do I do?"** Insight always pairs with an action
   (a nudge, a default-swap, an off-peak shift).
4. **Reduction feels like growth, not guilt.** Positive framing, collective context, no
   shaming. We avoid the "individual-blame" trap called out in DESIGN.md §8.
5. **Privacy is visible, not buried.** Consent state and data-degradation level are
   first-class, always reachable, symmetric to revoke.

---

## 2. Brand & Visual Identity

| Element | Direction |
|---|---|
| **Name mark** | "Carbonizer" set in the display face; the "O" rendered as a small ringed planet/leaf glyph that can animate (the brand's living-planet motif in miniature). |
| **Logo behavior** | The planet "O" subtly reflects app state on the dashboard header (greener when improving). Static everywhere else. |
| **Voice** | Calm, encouraging, precise. "You're trending 8% below your neighborhood." Never "You failed your goal." |
| **Imagery** | 3D rendered nature over stock photography. Soft volumetric light, no harsh corporate gradients. |
| **Iconography** | Lucide-style 1.75px line icons, rounded joins; category icons get a duotone treatment using the category hue. |

---

## 3. Design Tokens

These are the source of truth. Ship as CSS custom properties + a Tailwind theme + a JSON
export for the Three.js scene.

### 3.1 Color — Dark (default)

```
/* Base / surfaces */
--bg-base:        #06110D;   /* app background, deep green-black            */
--bg-sunken:      #040C09;   /* wells, behind cards                          */
--surface-1:      #0E1C16;   /* primary card                                 */
--surface-2:      #15271E;   /* raised card / popover                        */
--surface-glass:  rgba(20, 39, 30, 0.55);  /* glassmorphic panels (blur 18px)*/
--border-subtle:  rgba(255,255,255,0.06);
--border-strong:  rgba(255,255,255,0.12);

/* Brand greens */
--brand-500:      #2BD576;   /* primary action, "healthy" state              */
--brand-400:      #4FE08C;   /* hover / glow                                 */
--brand-600:      #1FAE5E;   /* pressed                                      */
--brand-glow:     rgba(43,213,118,0.35);

/* Text */
--text-hi:        #EAF6EF;   /* headlines, numbers                           */
--text-mid:       #A7BEB2;   /* body                                         */
--text-lo:        #6E847A;   /* captions, axis labels                        */

/* Category accents (used in viz + biome) */
--cat-transport:  #38BDF8;   /* sky/cyan   */
--cat-energy:     #FBBF24;   /* amber/gold */
--cat-food:       #A3E635;   /* lime       */
--cat-spend:      #C084FC;   /* violet     */
--cat-home:       #FB923C;   /* orange     */

/* Semantic */
--success:        #34D399;
--warning:        #FBBF24;
--danger:         #F87171;   /* high-emission, never punitive red-alert      */
--info:           #60A5FA;
```

### 3.2 Color — Light (secondary)

Light mode is for daytime/outdoor and accessibility. Invert surfaces to warm off-whites,
keep brand green, darken text. Biome shifts to a daytime sky.

```
--bg-base:    #F4F8F5;   --surface-1: #FFFFFF;   --surface-2: #EDF3EE;
--text-hi:    #0B1F16;   --text-mid:  #3C5249;   --text-lo:   #6B8175;
--brand-500:  #16A34A;   /* AA-safe on white */
```

### 3.3 Typography

| Role | Font | Notes |
|---|---|---|
| Display / headings | **Clash Display** (or Satoshi) | Geometric, confident. H1–H3 only. |
| Body / UI | **Inter** | `font-feature-settings: "cv05","ss01"`. |
| Numerals / data | **Inter** with `font-variant-numeric: tabular-nums` | Tabular for all metrics so digits don't jitter when live-updating. |
| Mono (codes/IDs) | **IBM Plex Mono** | MPAN/MPRN, transaction refs. |

**Type scale (rem, 1rem = 16px):**
`Display 3.5 / H1 2.5 / H2 2.0 / H3 1.5 / H4 1.25 / Body-lg 1.125 / Body 1.0 / Caption 0.875 / Micro 0.75`.
Line-height: 1.15 for display, 1.5 for body. Headlines tracked −1%.

### 3.4 Spacing, Radius, Elevation

```
Spacing scale (px): 2 4 8 12 16 20 24 32 40 48 64 80 96
Radius: sm 8 · md 12 · lg 16 · xl 24 · pill 999 · card 20
Shadows (dark uses glow not drop):
  --elev-1: 0 1px 0 rgba(255,255,255,.04) inset, 0 8px 24px rgba(0,0,0,.35)
  --elev-glow: 0 0 0 1px var(--brand-glow), 0 0 32px var(--brand-glow)
Blur: glass 18px, scrim 8px
```

### 3.5 Motion Tokens

```
--ease-out:    cubic-bezier(0.16, 1, 0.3, 1)    /* default UI entrance     */
--ease-inout:  cubic-bezier(0.65, 0, 0.35, 1)
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1)/* reward pops             */
Durations: instant 80ms · fast 160ms · base 240ms · slow 400ms · scene 800ms
```

All motion respects `prefers-reduced-motion` (see §11).

---

## 4. The Signature 3D Experience — "Living Planet"

A personal low-poly planet/island floats at the heart of the dashboard. Its health is a
direct, continuous read-out of the user's rolling carbon footprint vs. their personalized
target. This is the product's emotional engine and the literal embodiment of the
"tangible equivalents" nudge.

### 4.1 What maps to what

| Footprint signal | Biome response |
|---|---|
| Overall footprint vs. target | Global health: lush & green (good) → arid/grey, retreating ice, hazy sky (poor). Interpolated, never binary. |
| Transport emissions | Roads/vehicles density; haze layer over the planet. |
| Energy emissions | Sky color + a small grid/turbine cluster; turbines spin with renewable share. |
| Food emissions | Farmland tint and crop density. |
| Spend emissions | "Consumption" particles / freight ships orbiting. |
| A logged reduction / streak | A **tree plants with a spring pop**, ice reforms, a creature appears — the reward moment. |
| Real-time grid carbon intensity | Day/night sky + a subtle "clean energy now" green aurora when intensity is low (ties to off-peak nudge). |

### 4.2 States

- **Onboarding (seed state):** a small barren islet — "Let's bring your world to life."
- **Healthy / improving:** saturated greens, clear sky, wildlife, gentle bloom.
- **Plateau:** neutral, calm, slow drift.
- **Regressing:** desaturation, drifting haze, sky dims. *Tone stays hopeful* — copy frames
  it as "your world needs attention," paired with one tappable fix.
- **Celebration:** triggered on goal/streak/challenge completion — burst of growth, particle
  confetti made of leaves, camera dolly-in.

### 4.3 Interactions

- **Orbit / pinch-zoom** the planet (OrbitControls, damped, clamped).
- **Tap a region** (farmland, grid, roads) → that category's insight panel slides in
  (the 3D doubles as navigation).
- **Hotspots** float as small glass pins on contributing regions; hover/long-press shows a
  micro-stat.
- **Scrubber:** a timeline ring lets users scrub the last 12 weeks and watch the world
  evolve — powerful for showing progress.

### 4.4 Performance & "Green AI" budget

The 3D must honor the project's own Green-AI ethic (DESIGN.md §7) and run on mid-range
hardware:

- **Budget:** ≤ 60k triangles, single draw-call instancing for trees/particles, target
  60fps desktop / 30fps mobile, GPU memory < 150MB.
- **Adaptive quality:** auto-detect via `WebGLRenderer` capabilities + dynamic DPR
  (`react-three-fiber` `<PerformanceMonitor>`); drop shadows/bloom on low tier.
- **Pause when offscreen / tab hidden** (`frameloop="demand"` — only render on state change
  or interaction, not a constant RAF loop). This is both perf and battery/carbon hygiene.
- **Lazy-load** the scene with `next/dynamic` (`ssr:false`) behind a static poster image so
  first paint and Lighthouse aren't penalized.

### 4.5 Accessibility fallback (mandatory)

The biome is **decorative-augmentative, never the only source of information.**

- With `prefers-reduced-motion`: render a **static, high-quality poster** of the current
  state + a text/badge summary ("Your world: Recovering — 8% below target").
- Every region/hotspot has a non-3D equivalent in the cards below; keyboard users navigate
  cards, not the canvas.
- The canvas carries `role="img"` with a live `aria-label` describing current state, updated
  on significant change (debounced, polite live region).
- A **"2D mode" toggle** in settings disables WebGL entirely for low-power or
  motion-sensitive users.

---

## 5. Information Architecture

```
Carbonizer
├── Onboarding (unauthenticated → first-run)
│   ├── Welcome / value
│   ├── Account + consent basics
│   ├── Connect data  ── Open Banking · Telematics · Smart Meter (any/all, skippable)
│   └── Baseline reveal (first biome render)
├── Dashboard            ← home, the 3D hero + glance cards
├── Insights
│   ├── Overview (stacked trend, category split)
│   ├── Transport · Energy · Food · Spend  (drill-downs)
│   └── Transactions / activity ledger
├── Act (Recommendations)
│   ├── Suggested actions feed
│   ├── Default-swaps
│   └── Off-peak / low-carbon-now alerts
├── Community
│   ├── Benchmark (vs. similar households)
│   ├── Challenges
│   └── Achievements / streaks
└── Profile & Settings
    ├── Goals & targets
    ├── Connections (manage data sources)
    ├── Privacy & Data  ── consent, degradation level, export, erasure
    └── Appearance (theme, 2D mode, motion)
```

### Navigation pattern

- **Desktop:** left vertical rail (collapsed icons → expands on hover) with 5 primary
  destinations: Dashboard · Insights · Act · Community · Profile. Persistent footprint
  "pill" at the top of main content.
- **Mobile:** bottom tab bar (same 5), large thumb targets (min 48px). The 3D hero scales
  down but stays on Dashboard.
- **Command palette** (⌘K) for power users — jump to any category, action, or setting.

---

## 6. Key Screens

### 6.1 Onboarding & Data Connect

The make-or-break flow — friction here loses users (DESIGN.md §3). Goal: *time-to-first-biome
under 90 seconds*, with connections feeling safe.

**Steps**

1. **Welcome (3D teaser).** A demo biome breathing in the background. One line:
   "Automatically see — and shrink — your carbon footprint." CTA: *Get started*.
2. **Account.** Email/passwordless or OAuth. Minimal fields.
3. **The promise of consent.** Before any connect button, a plain-language card: *what* we
   read, *why*, *never* sold, revoke anytime. (DESIGN.md §10.) This is a trust gate, not fine print.
4. **Connect sources (the core).** Three large cards — **Bank**, **Travel**, **Home Energy** —
   each:
   - Shows the *one* thing it unlocks ("Bank → see the carbon in your spending").
   - A granular consent sheet on tap (scopes, retention, region) before redirect to the
     provider (PSD2 bank, telematics permission, meter linking).
   - Clearly **skippable** — "I'll do this later." Never block on all three.
   - State chips: *Connect → Connecting → Connected ✓ / Needs attention*.
5. **While we crunch.** A delightful loading state: the seed-islet begins to grow as data
   arrives, with progressive status ("Reading 3 months of transactions… classifying…").
6. **Baseline reveal.** The first full biome render + headline footprint and the single
   biggest lever. CTA into the dashboard.

**Design notes:** progress is a 5-dot stepper; each step independently resumable. Consent
sheets reuse one component (§7) so the legal surface is consistent and auditable.

### 6.2 Dashboard (home)

The glanceable command center. Above-the-fold, no scrolling needed for the core read.

**Layout (desktop, 12-col):**

```
┌───────────────────────────────────────────────────────────────┐
│  Footprint pill: 4.2 t CO₂e /yr  ·  ▼8% vs last mo  ·  ●Improving│
├──────────────────────────────┬────────────────────────────────┤
│                              │  This week                     │
│      [ LIVING PLANET 3D ]    │  ┌──────────┐ ┌──────────┐     │
│        interactive hero      │  │Transport │ │ Energy   │     │
│        (orbit, tap regions)  │  │ 1.1t ▲   │ │ 0.8t ▼   │     │
│                              │  └──────────┘ └──────────┘     │
│   "Your world is recovering" │  ┌──────────┐ ┌──────────┐     │
│                              │  │  Food    │ │  Spend   │     │
│                              │  │ 0.6t —   │ │ 1.7t ▼   │     │
│                              │  └──────────┘ └──────────┘     │
├──────────────────────────────┴────────────────────────────────┤
│  Do this next  →  [ Shift EV charge to 1am · save 0.4kg & £0.80 ]│
│  Benchmark      →  You're 8% below similar homes  ▕▏▕▏▕▏        │
└───────────────────────────────────────────────────────────────┘
```

**Components:** Footprint pill (live, tabular nums) · 3D hero · 4 category stat cards
(sparkline + trend arrow + category hue) · "Do this next" single high-impact nudge
· benchmark strip. Everything is a tap-through.

**Empty/first-run:** if only partial data, cards show "Connect Travel to fill this in" CTAs;
the biome shows the corresponding region as undeveloped rather than fake data. **We never
fabricate data** — missing = explicitly missing.

### 6.3 Insights & Breakdown

For System-2 users who want the numbers.

- **Overview:** a stacked area trend (12 wk default, range switch D/W/M/Y) with category
  legend; a donut of the period split; method badges (Activity-based ✓ / Spend-based ~)
  so users see data quality, honoring DESIGN.md's two modalities.
- **Category drill-down (e.g., Energy):** time-of-use heatmap (half-hourly × day),
  overlaid with **grid carbon intensity** and tariff price — the dual cost/carbon story.
  Highlights "your cleanest/dirtiest hours."
- **Transport:** trip ledger with detected mode chips (🚗🚌🚆🚲), distance, gCO₂e, and a
  small map snippet per trip; mode-share donut.
- **Activity ledger:** searchable, filterable transaction/event list. Each row: merchant/
  activity, amount, category, CO₂e, and a **method tag**. Users can correct a
  misclassification (feeds the NLP model) via an inline edit — surfaced gently, not nagging.

**Data-viz rules:** category colors are fixed across the entire app; always label units
(kg/t CO₂e); show confidence/method; never a pie with >5 slices (group the tail).

### 6.4 Act — Recommendations / Nudges

The behavioral core (DESIGN.md §8). A prioritized feed of *doable* actions, each with the
projected **carbon + money** saving (dual incentive).

- **Card anatomy:** icon · plain action ("Switch to a renewable tariff") · impact chips
  ("−0.3 t/yr · −£140/yr") · effort tag (1-tap / 5-min / setup) · primary CTA · dismiss.
- **Default-swaps:** framed as toggles where the low-carbon choice is *pre-selected*
  (status-quo bias), e.g., "Default new deliveries to no-rush shipping."
- **Off-peak / clean-now alert:** a time-sensitive banner when grid intensity is low —
  "Clean energy window until 4pm — run the dishwasher now." Mirrors the biome's aurora state.
- **Framing guardrail:** a recurring "You + others" module ties personal action to collective
  impact, countering the disempowerment trap.

### 6.5 Community — Social & Gamification

Normative influence drives the biggest reductions (DESIGN.md §8), but must avoid shaming.

- **Benchmark:** "Households like yours" (matched on size + income, CoolClimate-style). A
  horizontal gauge: you vs. average vs. top 20%. Contextual, opt-in, privacy-safe
  (aggregates only).
- **Challenges:** time-boxed, joinable ("Car-free week"), with a shared progress bar and
  the biome reflecting collective wins.
- **Achievements & streaks:** collectible badges that *plant permanent features in your
  biome* (a grove, a returned species) — intrinsic, lasting rewards over points-chasing.
- **Leaderboards:** **friends/cohort only, opt-in**, framed positively (improvement %, not
  absolute footprint, so smaller households aren't unfairly "winning"). Never global public
  shaming.

### 6.6 Profile, Settings & Privacy

Privacy is a feature here, designed to be *legible*.

- **Connections:** each data source with status, last sync, scopes, and a one-tap
  disconnect. Disconnect is **as easy as connect** (symmetric, DESIGN.md §10).
- **Privacy & Data center:**
  - **Data degradation slider:** *Precise → 1km grid → Event-only (on-device)* — visually
    explains the trade-off (accuracy vs. privacy), mapping to the Tracelet-style levels.
  - **Retention:** shows the auto-erase clock; honors the inactivity policy with advance
    notice surfaced in-app.
  - **Export** (one tap, JSON/CSV) and **Erase everything** (clear, double-confirm,
    irreversible — styled distinctly but accessible).
  - **Consent log:** human-readable history of grants/withdrawals.
- **Goals:** set/adjust the personalized target the biome measures against.
- **Appearance:** theme (system/dark/light), **2D mode**, **reduce motion**, units (metric/
  imperial), language.

---

## 7. Component Library (v1)

Built as a typed React component set (shadcn/ui-style primitives + custom), themed via
tokens.

**Primitives:** Button (primary/secondary/ghost/danger, 3 sizes) · IconButton · Input/Select/
Combobox · Toggle/Switch · Checkbox/Radio · Slider · Tabs · Tooltip · Popover · Dialog/Sheet ·
Toast · Badge/Chip · Avatar · Progress (linear/ring) · Skeleton · Segmented control.

**Composite / domain:**
- **StatCard** — metric + trend arrow + sparkline + category hue.
- **FootprintPill** — live total, delta, status dot.
- **NudgeCard** — action + dual-impact chips + effort tag.
- **ConsentSheet** — reusable scoped-consent surface (the only place consent is asked).
- **ConnectionCard** — source status + manage.
- **BenchmarkGauge** — you vs. peers.
- **MethodBadge** — Activity-based ✓ / Spend-based ~ / Estimated.
- **CarbonChart** — themed wrapper over the charting lib (stacked area, donut, heatmap).
- **BiomeCanvas** — the R3F scene wrapper with poster fallback + 2D mode + a11y label.
- **AchievementBadge**, **ChallengeCard**, **TripRow**, **LedgerRow**.

Each component documented with: anatomy, props, all states (default/hover/focus/active/
disabled/loading/error/empty), and a11y notes.

---

## 8. Motion Design

Motion reinforces meaning; it's never decorative-for-its-own-sake (also a Green-AI stance —
fewer wasted frames).

| Pattern | Spec |
|---|---|
| Page/route transition | 240ms cross-fade + 8px rise, `--ease-out`. |
| Card entrance (lists) | staggered 40ms, fade+rise, capped at first ~8 items. |
| Number tick | metrics count up over 400ms `--ease-inout` (skipped under reduced-motion). |
| Reward (badge/streak) | spring pop `--ease-spring` + biome tree-plant; haptic on mobile. |
| Nudge dismiss | swipe/slide-out 160ms. |
| Biome state change | 800ms eased interpolation between scene states; never a hard cut. |
| Loading | branded skeleton shimmer; the onboarding "growing islet" for long crunches. |

Global rule: under `prefers-reduced-motion`, all transforms collapse to opacity-only (or
instant); the count-up shows final value immediately; biome → static poster.

---

## 9. Dark & Light Mode

- **Dark is default** (premium, makes the biome glow). Light mode fully supported and
  AA-validated.
- Tokens swap via `data-theme`; the Three.js scene subscribes to the theme token export and
  shifts sky/lighting (night ↔ day) accordingly.
- No pure-black/pure-white; shadows become glows in dark, soft drop-shadows in light.
- Charts re-map: category hues stay constant, but gridlines/axis use theme `--text-lo`.

---

## 10. Responsive Behavior

| Breakpoint | Layout |
|---|---|
| `< 640` (mobile) | Single column; bottom tab bar; biome 1:1, simplified (lower poly, no bloom); cards stack; charts horizontally scrollable. |
| `640–1024` (tablet) | 2-col card grid; rail collapsed to icons; biome ~40vh. |
| `≥ 1024` (desktop) | 12-col; expandable rail; biome as left hero; cards right. |
| `≥ 1440` | Max content width 1320px, centered; more breathing room. |

Touch targets ≥ 44–48px; the 3D canvas yields scroll on mobile (one-finger scrolls page,
two-finger orbits) to avoid scroll-trapping.

---

## 11. Accessibility (target: WCAG 2.1 AA)

- **Contrast:** body text ≥ 4.5:1, large text/UI ≥ 3:1 on every surface (validated for both
  themes; the deep-green base was tuned for this).
- **Color independence:** trends and categories never rely on color alone — always paired
  with an icon, arrow, label, or pattern (critical for the category viz and red/green
  improving states).
- **Keyboard:** full operability; visible focus ring (`--brand-400`, 2px offset); logical
  tab order; ⌘K palette; canvas is skippable (not a tab trap).
- **Screen readers:** semantic landmarks; charts have a text/table alternative; the biome is
  `role="img"` with a live-updated description; live regions are *polite* and debounced.
- **Motion & vestibular:** `prefers-reduced-motion` honored everywhere; explicit "Reduce
  motion" and "2D mode" toggles independent of the OS setting.
- **Forms:** labels always visible (no placeholder-as-label); inline errors with text +
  icon; consent controls are large and unambiguous.
- **Targets & spacing:** min 44px, 8px min gap between interactive elements.

---

## 12. Frontend Implementation Notes (Next.js + Three.js)

- **App Router**, server components for static shell, client components for the canvas and
  live data. Stream the dashboard shell; hydrate the biome after.
- **3D:** `@react-three/fiber` + `@react-three/drei` (OrbitControls, Environment,
  Instances, Html, PerformanceMonitor); `frameloop="demand"`; `next/dynamic({ ssr:false })`
  behind a poster. Keep all scene state in a small store (Zustand) fed by the data layer so
  the biome and cards read one source of truth.
- **Styling:** Tailwind with the token theme; CSS vars for runtime theme swap; Radix
  primitives under custom components.
- **Charts:** Visx or ECharts (themeable, accessible) wrapped in `CarbonChart`.
- **Data:** TanStack Query against FastAPI; optimistic UI for classification corrections
  and nudge dismissals.
- **Assets:** Draco-compressed glTF for biome meshes; texture atlases; lazy-load per tier.

---

## 13. Developer Handoff — Frontend ⇄ FastAPI Touchpoints

Design implies these data contracts (FastAPI to define/confirm):

| UI surface | Needs from API |
|---|---|
| Footprint pill / biome | `GET /footprint/summary` → total, period delta, status, per-category totals, target. |
| Biome state | derived client-side from summary + `GET /grid/intensity` (live) for the aurora/sky. |
| Category drill-down | `GET /insights/{category}?range=` → series, method tags, trips/transactions. |
| Energy heatmap | `GET /energy/consumption` (half-hourly) + `/energy/tariff` + `/grid/intensity`. |
| Ledger + correction | `GET /transactions`, `PATCH /transactions/{id}/category` (feeds NLP retraining). |
| Nudges | `GET /recommendations` → ranked actions w/ carbon+£ impact, effort, type. |
| Benchmark | `GET /community/benchmark` → cohort aggregates only (no PII). |
| Connections | `GET/POST/DELETE /connections/{bank|telematics|meter}` + consent scopes. |
| Privacy | `GET /privacy/consent-log`, `POST /privacy/export`, `DELETE /account`, degradation-level setting. |

**Handoff package:** token JSON, component specs with states, this doc, responsive
redlines, the biome state-map table, and a11y annotations per component.

---

## 14. Open UI Questions

- **Biome art style:** stylized low-poly (lighter, on-brand) vs. semi-realistic
  (heavier, more awe). Recommend low-poly for the perf/Green-AI budget.
- **Default landing:** Dashboard for everyone, or a "Today" digest for returning users?
- **Notifications:** how aggressive should clean-energy-window alerts be (push vs. in-app
  only) before they become friction?
- **Benchmark cohorting:** confirm the minimum cohort size for privacy-safe aggregates.

---

*Living document — revise as research, the design system, and the FastAPI contract solidify.*
