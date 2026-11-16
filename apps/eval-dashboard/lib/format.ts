// Display formatting for evaluation SHARES and COUNTS from the evidence pack (k/n shares, CIs, test counts).
// These are measurement results, not risk probabilities: risk values on this page render only through
// LockedNumber (P-01). Formatting is Intl only; no arithmetic is done here.
// One fractional digit matches services/eval/out/evidence.md ("62.1%", "100.0%").

const numLocale = (locale: string) => (locale === "ar" ? "ar-AE-u-nu-latn" : "en");

export function pct(share: number, locale: string): string {
  return new Intl.NumberFormat(numLocale(locale), { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(share);
}

/** Whole-percent form for targets (">= 85%"), as written in docs/00-CHARTER.md. */
export function pctTarget(share: number, locale: string): string {
  return new Intl.NumberFormat(numLocale(locale), { style: "percent", maximumFractionDigits: 1 }).format(share);
}

export function count(n: number, locale: string): string {
  return new Intl.NumberFormat(numLocale(locale)).format(n);
}

/** Build/sync timestamps are metadata shown LTR in both locales, so one fixed format avoids mixed-direction garbling. */
export function utc(iso: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(iso)) + " UTC";
}
