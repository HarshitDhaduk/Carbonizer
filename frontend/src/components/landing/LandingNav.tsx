import Link from "next/link";
import { Logo } from "@/components/layout/Logo";
import { OpenAppButton } from "./OpenAppButton";

export function LandingNav() {
  return (
    <header className="sticky top-0 z-50">
      <div className="glass mx-auto mt-3 flex max-w-6xl items-center justify-between rounded-pill px-4 py-2.5 md:px-6">
        <Link href="/" aria-label="Carbonizer home">
          <Logo />
        </Link>
        <nav className="hidden items-center gap-8 text-sm text-text-mid md:flex">
          <a href="#how" className="transition-colors hover:text-text-hi">
            How it works
          </a>
          <a href="#sources" className="transition-colors hover:text-text-hi">
            Your data
          </a>
          <a
            href="#principles"
            className="transition-colors hover:text-text-hi"
          >
            Principles
          </a>
        </nav>
        <OpenAppButton />
      </div>
    </header>
  );
}
