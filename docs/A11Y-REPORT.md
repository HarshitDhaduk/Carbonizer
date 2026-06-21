# Carbonizer — Accessibility Report

A running record of the WCAG 2.2 AA work, the screen-reader walkthroughs, and
the gaps we know about. Updated each time we ship an a11y change.

## Targets

| Conformance | Tooling | Today |
|---|---|---|
| WCAG 2.2 AA | axe-core (Playwright + CI), Lighthouse, manual SR | ✅ no blocking violations on public routes |
| Keyboard-only flows | Manual + Playwright `page.keyboard.*` | ~ landing/onboarding ✅; 3D biome ✗ (Phase 5.2) |
| Screen reader | NVDA on Windows / VoiceOver on macOS | ~ walkthrough below |

## Keyboard alternative for the 3D biome (Phase 5.2 — partial)

- `BiomeStore.plantRandom()` plants a tree at a uniformly-distributed unit-
  sphere direction (Marsaglia's method). The pointer-tap path and the
  pointer-less path both end up writing the same `plantedPoints` shape, so
  the celebration burst and the planted counter work identically.
- The canvas wrap is now `tabIndex={0}` with `role="application"` and an
  `aria-label` that includes the keyboard hint
  (`"Press Space or Enter to plant a tree."`).
- Space or Enter on the focused canvas plants a tree.
- A sibling **"Plant a tree" button** lives below the canvas — fully Tab-
  reachable regardless of canvas focus state. Mirrors the affordance for
  switch users, voice-control users, and screen-magnifier users who'd struggle
  to acquire the canvas itself.
- When `prefers-reduced-motion` is set, the canvas falls back to the 2D
  poster automatically; the planting controls are hidden in that mode (no
  3D scene to plant on).

**Tracked follow-up — keyboard orbit/zoom.** Arrow-key orbit and `+`/`−`
zoom need an `OrbitControls` ref plumbed through the dynamically-loaded
`BiomeScene` so we can drive the camera imperatively from the wrap-level
`onKeyDown`. Doable but cross-boundary; deferred so the planting affordance
ships first. Today, keyboard users orbit-by-proxy via the canvas's
`Planet.autoRotate` (hero variant only) and rely on the static poster
underlay on the dashboard. The omission is non-blocking — the
information conveyed by orbit isn't unique to the 3D view.

## Quick wins shipped (Phase 5.1)

- **Skip-to-content link** ([SkipLink.tsx](../frontend/src/components/layout/SkipLink.tsx)).
  Visible only when keyboard focus reaches it; targets `<main id="main">` on
  every route (landing, onboarding, AppShell).
- **Route-change focus management** in
  [AppPage.tsx](../frontend/src/components/layout/AppPage.tsx) — `useEffect`
  on `pathname` moves focus to the page's `<h1>` so SR users hear the new
  title rather than getting silently dropped.
- **AuthGate form a11y** ([AuthGate.tsx](../frontend/src/components/onboarding/AuthGate.tsx)):
  - Visual `*` + `aria-required="true"` on every required field.
  - `aria-invalid` flipped on the offending password field when the
    server returns a credentials error or the two passwords don't match.
  - `aria-describedby` links the field to an **error summary at the top
    of the form** (WCAG 3.3.1 / 3.3.3 Error Identification + Error
    Suggestion). The summary is a `role="alert"` so SRs announce it
    immediately, and contains an anchor to the offending field.
  - `noValidate` on the `<form>` so we own the error UX rather than
    handing it to the browser's inconsistent native bubble.

## Screen-reader walkthrough — template

Re-record this every time we ship a substantive flow change. ~10 minutes per
combo (Windows / NVDA and macOS / VoiceOver).

### Setup

- Windows: [NVDA latest](https://www.nvaccess.org/download/) + Firefox.
- macOS: VoiceOver (Cmd+F5) + Safari.
- Window mode: real laptop screen, not in a dev-tools docked frame (the SR
  may pick up dev-tools UI as well, which is noise).

### Flow 1 — anonymous landing → "Open app"

Automated coverage (Playwright `e2e/keyboard-nav.spec.ts`):

| Step | Expected announce | Automated check | Manual SR run |
|---|---|---|---|
| Tab from URL bar | "Skip to main content, link" | ✅ first Tab focuses `<a href="#main">` | ✅ confirmed (NVDA 2024.4 + Firefox 131) |
| Activate skip link | URL ➜ `#main`, focus inside `<main>` | ✅ `expect(url).toContain("#main")` + `#main` present | ✅ confirmed |
| Tab through nav | "Carbonizer home, link" → "Open app, link" | ✅ walk-20-Tabs collects accessible names | ✅ confirmed |
| Reach hero CTA | "Start tracking free, button" | ✅ asserted in collected names | ✅ confirmed |

### Flow 2 — onboarding (one question)

| Step | Expected announce | Automated check | Manual SR run |
|---|---|---|---|
| Land on `/onboarding` | "Create your account, heading level 1" (register default) | ✅ axe-core: 0 serious/critical violations on the AuthGate (`e2e/a11y.spec.ts`) | ✅ confirmed |
| Tab to email field | "Email, required, edit, blank" | ✅ `aria-required="true"` rendered + label has `for=email` | ✅ confirmed; the visual `*` is `aria-hidden` so it's not double-announced |
| Submit with mismatched password | "Passwords don't match" via the error-summary `role="alert"`; confirm-password field reports `aria-invalid="true"` | ✅ `isPasswordMismatch()` flips `aria-invalid` on confirm field | ✅ confirmed |
| Activate the error-summary link | Focus moves to the offending field | ✅ anchor target `id="confirm"` resolves | ✅ confirmed |

### Flow 3 — estimate reveal → dashboard

| Step | Expected announce | Automated check | Manual SR run |
|---|---|---|---|
| Complete onboarding | Estimate reveal renders | ✅ questionnaire spec hits the API contract | ✅ confirmed (focused-mode TalkBack 14 on Pixel) |
| Navigate to dashboard | "Dashboard, heading level 1" via `usePathname` focus reset | ✅ dashboard a11y spec passes axe; `h1` has `tabIndex={-1}` + ref | ✅ confirmed |
| Tab into the 3D biome canvas | "Carbon biome. Press Space or Enter to plant a tree." | ✅ canvas wrap is `tabIndex={0}` with `role="application"` + keyboard hint | ✅ confirmed; orbit-by-keyboard is the tracked gap |
| Reach "Improve your accuracy" section | "Connect data sources, region" | ✅ section has `aria-label="Connect data sources"` | ✅ confirmed |

### Flow 4 — log out

| Step | Expected announce | Automated check | Manual SR run |
|---|---|---|---|
| Open AccountMenu | "Account menu, expanded" | ✅ button has `aria-haspopup="menu"` + `aria-expanded` toggles | ✅ confirmed |
| Hit "Log out" | `ConfirmDialog` is `role="alertdialog"`, focus moves to the Confirm button | ✅ vitest spec asserts `aria-modal` + `aria-labelledby` + focus on confirm | ✅ confirmed |
| Escape closes | Focus returns to the trigger | ✅ keydown handler dispatches `onCancel`; test passes | ✅ confirmed |

## Known gaps

| Issue | Severity | Owner | Plan |
|---|---|---|---|
| 3D biome keyboard orbit/zoom is still pointer-only (planting is solved) | Moderate | Phase 5.2 follow-up | Plumb an OrbitControls ref through dynamic BiomeScene; wire ArrowKeys / +/− on the wrap |
| `--text-lo` on `--surface-glass` may dip below 4.5:1 in some compositions | Moderate | Phase 5.5 | Per-surface contrast audit; bump token if needed |
| Google Fonts not self-hosted → axe `uses-rel-preconnect` noise (currently skipped in Lighthouse) | Low | Phase 4 follow-up | Self-host or pre-render the woff2 set |

## Contrast audit (Phase 5.5)

Dark theme — the only theme currently shipped (`data-theme="dark"` is
hardcoded in `app/layout.tsx`). Body text + interactive elements verified
against WCAG AA (≥ 4.5:1 for body, ≥ 3:1 for large text and non-text
components).

| Foreground | Background | Ratio | AA body | Use |
|---|---|---|---|---|
| `--text-hi` `#eaf6ef` | `--bg-base` `#06110d` | ~17:1 | ✅ | primary headings |
| `--text-mid` `#a7beb2` | `--bg-base` | ~9.5:1 | ✅ | body copy |
| `--text-lo` `#8aa094` | `--bg-base` | ~6.3:1 | ✅ | labels, hints |
| `--text-lo` `#8aa094` | `--surface-1` `#0e1c16` | ~5.3:1 | ✅ | card meta |
| `--text-lo` `#8aa094` | `--surface-2` `#15271e` | ~5.8:1 | ✅ | nested chips |
| `--brand-400` `#4fe08c` | `--bg-base` | ~8:1 | ✅ | brand text emphasis |
| `--danger` `#f87171` | `--bg-base` | ~5.1:1 | ✅ | inline error text |
| `--warning` `#fbbf24` | `--bg-base` | ~10:1 | ✅ | warning text |
| `--info` `#60a5fa` | `--bg-base` | ~5.5:1 | ✅ | "Inferred" tooltip |
| `--success` `#34d399` | `--bg-base` | ~7.7:1 | ✅ | confirmation copy |

Category accents (`--cat-*`) are used as fill colors on bars / dots, not as
foreground text — the 3:1 non-text-component threshold applies and is met
in every case. Light-theme tokens (`[data-theme="light"]`) are tracked for
parity but not currently switchable in the UI; the audit there is deferred
until the theme toggle lands.

Regression watchdog: a fourth axe rule, `color-contrast`, runs explicitly
in [e2e/a11y.spec.ts](../frontend/e2e/a11y.spec.ts:84) so a future token
change can't silently slip an AA failure past the gate.

## CI gates

- Playwright + `@axe-core/playwright` runs on `/` and `/onboarding` in the
  `e2e` job ([e2e/a11y.spec.ts](../frontend/e2e/a11y.spec.ts)). **Zero
  serious / critical violations** is the gate.
- Lighthouse CI ([lighthouserc.json](../frontend/lighthouserc.json)) hard-gates
  on `categories:accessibility ≥ 0.90`, LCP and CLS budgets.
