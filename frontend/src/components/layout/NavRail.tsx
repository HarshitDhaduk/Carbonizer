"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "./nav-items";
import { Logo } from "./Logo";
import { cn } from "@/lib/cn";

/**
 * Desktop vertical rail — collapsed icons that expand labels on hover or
 * keyboard focus (docs/UI-UX-DESIGN.md §5). Hidden on mobile (MobileTabBar
 * takes over).
 *
 * The `focus-within` variants matter: with hover alone, a keyboard user tabbing
 * through primary navigation sees icons and never a label.
 */
export function NavRail() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Primary"
      className="group/rail hidden h-dvh w-16 shrink-0 flex-col items-center gap-1 border-r border-border-subtle bg-bg-sunken py-4 transition-[width] duration-base ease-out focus-within:w-56 hover:w-56 md:flex"
    >
      <Link
        href="/"
        aria-label="Carbonizer home"
        className="mb-4 flex h-9 w-full items-center px-4"
      >
        <Logo
          showWordmark={false}
          className="group-focus-within/rail:hidden group-hover/rail:hidden"
        />
        <Logo
          showWordmark
          className="hidden group-focus-within/rail:inline-flex group-hover/rail:inline-flex"
        />
      </Link>

      {NAV_ITEMS.map(({ href, label, Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex h-11 w-[calc(100%-1rem)] items-center gap-3 rounded-md px-3 transition-colors duration-fast",
              active
                ? "bg-brand-500/15 text-brand-400"
                : "text-text-lo hover:bg-surface-2 hover:text-text-hi",
            )}
          >
            <Icon size={20} aria-hidden className="shrink-0" />
            <span className="overflow-hidden whitespace-nowrap opacity-0 transition-opacity duration-base group-focus-within/rail:opacity-100 group-hover/rail:opacity-100">
              {label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
