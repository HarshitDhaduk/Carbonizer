import { Construction } from "lucide-react";

/** Placeholder for screens specced in docs/UI-UX-DESIGN.md but not yet built. */
export function ComingSoon({ title, note }: { title: string; note: string }) {
  return (
    <div className="animate-fade-rise flex min-h-[60dvh] flex-col items-center justify-center text-center">
      <span className="mb-4 grid h-14 w-14 place-items-center rounded-card bg-surface-2 text-brand-400">
        <Construction size={24} aria-hidden />
      </span>
      <h1 className="font-display text-2xl text-text-hi">{title}</h1>
      <p className="mt-2 max-w-md text-text-mid">{note}</p>
    </div>
  );
}
