import { ShieldCheck, Sparkles, Users } from "lucide-react";
import { type Card, CardGrid, SectionHeading } from "./section-primitives";

const CARDS: Card[] = [
  {
    Icon: Sparkles,
    title: "Nudges, not nagging",
    body: "Grounded in behavioral science: smart defaults and one-tap actions that fit your life — never guilt.",
    accent: "#2bd576",
  },
  {
    Icon: Users,
    title: "You vs. similar homes",
    body: "Positive, private benchmarking against households like yours. Aggregates only — never another person's data.",
    accent: "#60a5fa",
  },
  {
    Icon: ShieldCheck,
    title: "Privacy by design",
    body: "Consent-driven, purpose-limited, with on-device options and one-tap erasure. Your data is never sold.",
    accent: "#34d399",
  },
];

/** Our values, expressed in three cards. The closing section before the
 * final CTA — leaves the visitor on "this is the team that built it." */
export function Principles() {
  return (
    <section
      id="principles"
      className="mx-auto max-w-6xl px-4 py-16 md:px-6 md:py-24"
    >
      <SectionHeading
        eyebrow="Built right"
        title="Effective, honest, and light on the planet"
        blurb="Even our AI runs lean — edge-first models keep the tool itself low-carbon."
      />
      <CardGrid cards={CARDS} />
    </section>
  );
}
