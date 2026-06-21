/**
 * "Skip to main content" link — Phase 5.1 of docs/IMPROVEMENT-PLAN.md.
 *
 * Hidden until keyboard focus reaches it. Targets the page's `<main id="main">`
 * so keyboard / screen-reader users can bypass the nav rail on every route.
 */
export function SkipLink() {
  return (
    <a
      href="#main"
      className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-brand-500 focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-bg-base focus:shadow-elev-1 focus:outline-none focus:ring-2 focus:ring-brand-400"
    >
      Skip to main content
    </a>
  );
}
