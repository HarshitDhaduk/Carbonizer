import { Gauge, Landmark, Route } from "lucide-react";
import { type Card, CardGrid, SectionHeading } from "./section-primitives";

const CARDS: Card[] = [
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

/** "Where the data comes from" — the technical answer to the same question
 * HowItWorks asks at a marketing level. */
export function DataSources() {
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
        <CardGrid cards={CARDS} />
      </div>
    </section>
  );
}
