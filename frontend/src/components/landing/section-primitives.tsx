import { type LucideIcon } from "lucide-react";

/**
 * Visual primitives shared by every landing-page section.
 * Keeping them here means the section files stay focused on copy + structure,
 * and a typography or card-shape tweak ripples through every section once.
 */

export function SectionHeading({
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

export interface Card {
  Icon: LucideIcon;
  title: string;
  body: string;
  accent: string;
}

export function CardGrid({ cards }: { cards: Card[] }) {
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
