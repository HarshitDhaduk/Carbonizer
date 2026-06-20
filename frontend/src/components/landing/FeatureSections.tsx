import {
  Landmark,
  Route,
  Gauge,
  Sparkles,
  Users,
  Leaf,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { StartTrackingButton } from "./StartTrackingButton";

function SectionHeading({
  eyebrow,
  title,
  blurb,
}: {
  eyebrow: string;
  title: string;
  blurb?: string;
}) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <p className="text-sm font-medium uppercase tracking-wider text-brand-400">
        {eyebrow}
      </p>
      <h2 className="mt-2 font-display text-3xl text-text-hi md:text-4xl">
        {title}
      </h2>
      {blurb && <p className="mt-3 text-text-mid">{blurb}</p>}
    </div>
  );
}

interface Card {
  Icon: LucideIcon;
  title: string;
  body: string;
  accent: string;
}

function CardGrid({ cards }: { cards: Card[] }) {
  return (
    <div className="mx-auto mt-10 grid max-w-5xl gap-4 md:grid-cols-3">
      {cards.map(({ Icon, title, body, accent }) => (
        <div
          key={title}
          className="rounded-card border border-border-subtle bg-surface-1 p-6 transition-colors hover:border-border-strong"
        >
          <span
            className="grid h-11 w-11 place-items-center rounded-md"
            style={{ backgroundColor: `${accent}1f`, color: accent }}
          >
            <Icon size={20} aria-hidden />
          </span>
          <h3 className="mt-4 font-medium text-text-hi">{title}</h3>
          <p className="mt-1.5 text-sm text-text-mid">{body}</p>
        </div>
      ))}
    </div>
  );
}

// ── How it works ─────────────────────────────────────────────────────────

function HowItWorks() {
  const steps = [
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
  return (
    <section id="how" className="mx-auto max-w-6xl px-4 py-16 md:px-6 md:py-24">
      <SectionHeading
        eyebrow="How it works"
        title="From passive worry to measurable action"
        blurb="Most footprint apps die on manual data entry. Carbonizer automates the whole pipeline so the only thing you do is improve."
      />
      <div className="mx-auto mt-10 grid max-w-4xl gap-4 md:grid-cols-3">
        {steps.map((s) => (
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

// ── Data sources ───────────────────────────────────────────────────────────

function DataSources() {
  const cards: Card[] = [
    {
      Icon: Landmark,
      title: "Open Banking",
      body: "Spending is classified and priced for carbon with scientifically-vetted emission factors — not blunt category codes.",
      accent: "#c084fc",
    },
    {
      Icon: Route,
      title: "Travel telematics",
      body: "Trips are detected automatically and measured by mode and distance — battery-friendly, fully on-device.",
      accent: "#38bdf8",
    },
    {
      Icon: Gauge,
      title: "Smart meter",
      body: "Half-hourly energy use is matched to real-time grid intensity, so you see — and time — your cleanest hours.",
      accent: "#fbbf24",
    },
  ];
  return (
    <section
      id="sources"
      className="bg-bg-sunken/60 border-y border-border-subtle py-16 md:py-24"
    >
      <div className="mx-auto max-w-6xl px-4 md:px-6">
        <SectionHeading
          eyebrow="Your data, working for you"
          title="Three signals, one accurate footprint"
          blurb="Activity-based where it counts, spend-based for breadth — reconciled into a single CO₂e number you can trust."
        />
        <CardGrid cards={cards} />
      </div>
    </section>
  );
}

// ── Principles ───────────────────────────────────────────────────────────

function Principles() {
  const cards: Card[] = [
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
      <CardGrid cards={cards} />
    </section>
  );
}

// ── Final CTA ──────────────────────────────────────────────────────────────

function FinalCta() {
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

export function FeatureSections() {
  return (
    <>
      <HowItWorks />
      <DataSources />
      <Principles />
      <FinalCta />
    </>
  );
}
