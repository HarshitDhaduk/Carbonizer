import { Logo } from "@/components/layout/Logo";

export function LandingFooter() {
  return (
    <footer className="border-t border-border-subtle">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 text-sm text-text-lo md:flex-row md:px-6">
        <Logo />
        <p>Track less. Live better. © {2026} Carbonizer.</p>
        <nav className="flex gap-6">
          <a href="#" className="transition-colors hover:text-text-hi">
            Privacy
          </a>
          <a href="#" className="transition-colors hover:text-text-hi">
            Methodology
          </a>
        </nav>
      </div>
    </footer>
  );
}
