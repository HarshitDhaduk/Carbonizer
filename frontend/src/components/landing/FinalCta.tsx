import { Leaf } from "lucide-react";
import { StartTrackingButton } from "./StartTrackingButton";

/** Closing CTA card at the very bottom of the landing page — the one a
 * visitor sees right before they decide whether to scroll back up or sign up. */
export function FinalCta() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-20 md:px-6">
      <div className="relative overflow-hidden rounded-card border border-border-subtle bg-surface-1 px-6 py-14 text-center">
        <div
          aria-hidden
          className="bg-brand-500/15 pointer-events-none absolute inset-x-0 top-0 mx-auto h-64 w-[480px] rounded-full blur-[100px]"
        />
        <Leaf size={28} aria-hidden className="mx-auto text-brand-400" />
        <h2 className="mt-4 font-display text-3xl text-text-hi md:text-4xl">
          Your planet is waiting.
        </h2>
        <p className="mx-auto mt-3 max-w-md text-text-mid">
          Connect your first account and watch the change in minutes.
        </p>
        <StartTrackingButton className="mt-8" />
      </div>
    </section>
  );
}
