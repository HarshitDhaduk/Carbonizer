import { DataSources } from "./DataSources";
import { FinalCta } from "./FinalCta";
import { HowItWorks } from "./HowItWorks";
import { Principles } from "./Principles";

/**
 * Composes the four below-the-fold sections of the landing page in order.
 * Each section is its own file so a copy or layout edit ripples through
 * one focused module rather than this composer.
 */
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
