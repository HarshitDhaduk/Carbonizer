import { DataSources } from "./DataSources";
import { FinalCta } from "./FinalCta";
import { HowItWorks } from "./HowItWorks";
import { Principles } from "./Principles";
import { WhyThisIsHard } from "./WhyThisIsHard";

/**
 * Composes the below-the-fold sections of the landing page in order:
 * HowItWorks → WhyThisIsHard → DataSources → Principles → FinalCta.
 * Each section is its own file so a copy or layout edit ripples through
 * one focused module rather than this composer.
 *
 * WhyThisIsHard sits between the marketing-side HowItWorks and the
 * technical-side DataSources — it makes the problem-statement alignment
 * visible to a visitor who never opens the docs.
 */
export function FeatureSections() {
  return (
    <>
      <HowItWorks />
      <WhyThisIsHard />
      <DataSources />
      <Principles />
      <FinalCta />
    </>
  );
}
