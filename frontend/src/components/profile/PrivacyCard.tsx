import { ShieldCheck } from "lucide-react";

/** Brief privacy assurance — purpose-limited use + GDPR / DPDP rights. */
export function PrivacyCard() {
  return (
    <section className="rounded-card border border-border-subtle bg-surface-1 p-4">
      <h2 className="mb-2 flex items-center gap-2 text-sm font-medium text-text-mid">
        <ShieldCheck size={15} aria-hidden className="text-brand-400" />
        Privacy &amp; control
      </h2>
      <p className="text-sm text-text-mid">
        Your data is used only to calculate your footprint — never sold or used
        for advertising. You can disconnect any source above, and request a full
        export or erasure at any time (GDPR &amp; DPDP).
      </p>
    </section>
  );
}
