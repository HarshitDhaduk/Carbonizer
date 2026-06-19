/** Display formatters. All metrics route through here for consistent rounding. */

/** Tonnes CO2e, e.g. 4.2 → "4.2 t". Switches to kg below 0.1 t, keeping a
 *  decimal for sub-kg values so small per-event savings never round to "0 kg". */
export function formatCo2e(tco2e: number): string {
  if (Math.abs(tco2e) < 0.1) {
    const kg = tco2e * 1000;
    return `${kg.toFixed(Math.abs(kg) < 10 ? 1 : 0)} kg`;
  }
  return `${tco2e.toFixed(1)} t`;
}

/** Signed percent, e.g. -8 → "8%" (sign conveyed separately by trend UI). */
export function formatPct(pct: number): string {
  return `${Math.abs(Math.round(pct))}%`;
}

export function formatMoney(amount: number, currency: string): string {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency,
    maximumFractionDigits: amount < 10 ? 2 : 0,
  }).format(amount);
}
