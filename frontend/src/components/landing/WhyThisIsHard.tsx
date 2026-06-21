import { SectionHeading } from "./section-primitives";

interface Problem {
  failure: string;
  userPain: string;
  solution: string;
}

const PROBLEMS: Problem[] = [
  {
    failure: "Manual logging tax",
    userPain:
      "Apps ask you to type every receipt, weigh every meal. Nobody does it past week 2.",
    solution:
      "Zero data entry after onboarding. Your bank, meter, and travel app already know.",
  },
  {
    failure: "Connect-three-things wall",
    userPain:
      "Only have a bank? Most apps refuse to give you a number until you connect everything.",
    solution:
      "R1 — bank-as-hub imputation. One source produces a usable, calibrated footprint with explicit confidence.",
  },
  {
    failure: "Spend-blind accounting",
    userPain:
      "Spend more on the sustainable shoes? Your score goes up. The product punishes you for caring.",
    solution:
      "R2 — per-merchant intensity multipliers + per-category price elasticity. £→CO₂e respects what you actually bought.",
  },
  {
    failure: "Cleaner-grid plagiarism",
    userPain:
      "Your energy emissions dropped 15% — but the UK grid just got 15% cleaner. The win wasn't yours.",
    solution:
      "R3 — behavioural-vs-structural decomposition. You're only credited for the change you actually drove.",
  },
  {
    failure: "Privacy theatre",
    userPain:
      "Being benchmarked against a cherry-picked sample of eco-skewed early adopters isn't honest.",
    solution:
      "R4 — IPW selection-bias correction + Laplace (ε)-DP + k-anonymity. Honest comparison, individuals protected.",
  },
];

/**
 * The "Why this is hard" landing section — makes the problem-statement
 * alignment visible to a visitor who never opens the docs.
 *
 * Each row pairs (a) a failure mode of every prior carbon-tracking app with
 * (b) what a real user felt because of it and (c) the specific Carbonizer
 * sub-system that resolves it. The pairing is the contribution — none of the
 * individual moves are novel, but shipping them together as one experience is.
 */
export function WhyThisIsHard() {
  return (
    <section
      id="why-hard"
      className="bg-bg-sunken/40 border-y border-border-subtle py-16 md:py-24"
    >
      <div className="mx-auto max-w-6xl px-4 md:px-6">
        <SectionHeading
          eyebrow="The five problems every carbon app hits"
          title="Why personal carbon-tracking apps die"
          blurb="A decade of dead apps left a paper trail. We picked the five recurring failure modes and made each one a design constraint."
        />
        <ol className="mx-auto mt-10 grid max-w-5xl gap-3 md:grid-cols-1">
          {PROBLEMS.map((p, i) => (
            <li
              key={p.failure}
              className="grid gap-3 rounded-card border border-border-subtle bg-surface-1 p-5 md:grid-cols-[auto_1fr_1fr] md:items-center"
            >
              <span
                aria-hidden
                className="text-brand-500/60 tnum font-display text-2xl"
              >
                0{i + 1}
              </span>
              <div>
                <h3 className="font-medium text-text-hi">{p.failure}</h3>
                <p className="mt-1 text-sm text-text-mid">{p.userPain}</p>
              </div>
              <p className="text-sm text-text-mid md:border-l md:border-border-subtle md:pl-4">
                <span className="text-brand-400">→ </span>
                {p.solution}
              </p>
            </li>
          ))}
        </ol>
        <p className="mx-auto mt-6 max-w-2xl text-center text-xs text-text-lo">
          Full traceability from each failure mode to the file that resolves it
          is in{" "}
          <a
            href="https://github.com/HarshitDhaduk/Carbonizer/blob/main/docs/PROBLEM-STATEMENT.md"
            className="underline hover:text-text-mid"
          >
            docs/PROBLEM-STATEMENT.md
          </a>
          .
        </p>
      </div>
    </section>
  );
}
