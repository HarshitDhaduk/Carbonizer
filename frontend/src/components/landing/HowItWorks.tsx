import { SectionHeading } from "./section-primitives";

const STEPS = [
  {
    n: "01",
    title: "Connect once",
    body: "Securely link your bank, travel and home energy. No receipts, no spreadsheets, no daily logging.",
  },
  {
    n: "02",
    title: "See it live",
    body: "Every transaction, trip and kilowatt-hour is mapped to CO₂e and rendered as your living planet.",
  },
  {
    n: "03",
    title: "Shrink it",
    body: "Get the handful of high-impact moves that cut the most carbon — and money — with one tap.",
  },
];

/** Three-step "how does this work" section — the marketing-side answer to
 * "what do I actually do?" — pairs with the technical detail in DataSources. */
export function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-6xl px-4 py-16 md:px-6 md:py-24">
      <SectionHeading
        eyebrow="How it works"
        title="From passive worry to measurable action"
        blurb="Most footprint apps die on manual data entry. Carbonizer automates the whole pipeline so the only thing you do is improve."
      />
      <div className="mx-auto mt-10 grid max-w-4xl gap-4 md:grid-cols-3">
        {STEPS.map((s) => (
          <div
            key={s.n}
            className="rounded-card border border-border-subtle bg-surface-1 p-6"
          >
            <span className="text-brand-500/70 tnum font-display text-2xl">
              {s.n}
            </span>
            <h3 className="mt-2 font-medium text-text-hi">{s.title}</h3>
            <p className="mt-1.5 text-sm text-text-mid">{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
