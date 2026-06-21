import { NavRail } from "./NavRail";
import { MobileTabBar } from "./MobileTabBar";

/** App chrome: desktop rail + mobile tab bar wrapping the routed content. */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh bg-bg-base">
      <NavRail />
      <main
        id="main"
        className="mx-auto w-full max-w-[1320px] flex-1 px-4 pb-24 pt-4 md:px-8 md:pb-8"
      >
        {children}
      </main>
      <MobileTabBar />
    </div>
  );
}
