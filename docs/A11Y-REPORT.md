# Carbonizer — Accessibility Report

A running record of the WCAG 2.2 AA work, the screen-reader walkthroughs, and
the gaps we know about. Updated each time we ship an a11y change.

## Targets

| Conformance | Tooling | Today |
|---|---|---|
| WCAG 2.2 AA | axe-core (Playwright + CI), Lighthouse, manual SR | ✅ no blocking violations on public routes |
| Keyboard-only flows | Manual + Playwright `page.keyboard.*` | ~ landing/onboarding ✅; 3D biome ✗ (Phase 5.2) |
| Screen reader | NVDA on Windows / VoiceOver on macOS | ~ walkthrough below |

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

| Step | Expected announce | NVDA today | VO today |
|---|---|---|---|
| Tab from URL bar | "Skip to main content, link" | _todo_ | _todo_ |
| Activate skip link | Focus jumps to the `<main>` content | _todo_ | _todo_ |
| Tab through nav | "Carbonizer home, link" → "Open app, link" | _todo_ | _todo_ |
| Reach hero CTA | "Start tracking free, button" | _todo_ | _todo_ |

### Flow 2 — onboarding (one question)

| Step | Expected announce | NVDA today | VO today |
|---|---|---|---|
| Land on `/onboarding` | "Welcome back, heading level 1" (login) **or** "Create your account, heading level 1" (register, default) | _todo_ | _todo_ |
| Tab to email field | "Email, required, edit, blank" | _todo_ | _todo_ |
| Submit with mismatched password | "Passwords don't match" announced via the error summary's `role="alert"`; confirm-password field reports `aria-invalid="true"` | _todo_ | _todo_ |
| Activate the error-summary link | Focus moves to the offending field | _todo_ | _todo_ |

### Flow 3 — estimate reveal → dashboard

| Step | Expected announce | NVDA today | VO today |
|---|---|---|---|
| Complete onboarding | Estimate reveal renders | _todo_ | _todo_ |
| Navigate to dashboard | "Dashboard, heading level 1" via the focus-on-route-change in AppPage | _todo_ | _todo_ |
| Tab into the 3D biome canvas | _todo_ — see Phase 5.2 gap below | _todo_ | _todo_ |
| Reach the "Improve your accuracy" section | "Connect data sources, region" | _todo_ | _todo_ |

### Flow 4 — log out

| Step | Expected announce | NVDA today | VO today |
|---|---|---|---|
| Open AccountMenu | "Account menu, expanded" | _todo_ | _todo_ |
| Hit "Log out" | The `ConfirmDialog` is `role="alertdialog"`, focus moves to the Confirm button | _todo_ | _todo_ |
| Escape closes | Focus returns to the trigger | _todo_ | _todo_ |

## Known gaps

| Issue | Severity | Owner | Plan |
|---|---|---|---|
| 3D biome is pointer-only — no `Plant a tree` button, no keyboard orbit | High | Phase 5.2 | Sibling button + KeyboardOrbitControls (ArrowKeys / +/−); canvas gains `tabIndex={0}` |
| `--text-lo` on `--surface-glass` may dip below 4.5:1 in some compositions | Moderate | Phase 5.5 | Per-surface contrast audit; bump token if needed |
| Google Fonts not self-hosted → axe `uses-rel-preconnect` noise (currently skipped in Lighthouse) | Low | Phase 4 follow-up | Self-host or pre-render the woff2 set |

## CI gates

- Playwright + `@axe-core/playwright` runs on `/` and `/onboarding` in the
  `e2e` job ([e2e/a11y.spec.ts](../frontend/e2e/a11y.spec.ts)). **Zero
  serious / critical violations** is the gate.
- Lighthouse CI ([lighthouserc.json](../frontend/lighthouserc.json)) hard-gates
  on `categories:accessibility ≥ 0.90`, LCP and CLS budgets.
