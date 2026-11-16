// Display-only de-duplication (DECISIONS #44, handoffs/REQUEST-UI-CIT-1.md).
// Hides ONLY these exact closed-template sentences from message bodies, and only on pages that already show the
// judicial callout + compliance footer. Delivered/stored messages are unchanged. Unknown wording is never touched.
const REPEATED_SENTENCES = [
  "The marriage health certificate is issued and sent to the Abu Dhabi Judicial Department regardless of your genetic results.",
  "This is decision support, not a diagnosis or medical advice.",
  "تُصدر الشهادة الصحية للزواج وتُرسل إلى دائرة القضاء في أبوظبي بغض النظر عن نتائج فحوصك الجينية.",
  "هذه المعلومات للمساعدة في اتخاذ القرار، وليست تشخيصاً ولا نصيحة طبية.",
] as const;

export function withoutPageNotices(text: string): string {
  let out = text;
  for (const s of REPEATED_SENTENCES) out = out.split(s).join("");
  return out.replace(/\s{2,}/g, " ").trim();
}

/** Condition name for a vault call: Arabic when available on the AR route, else English, else null (A3). */
export function conditionOf(c: { condition?: string | null; condition_ar?: string | null }, locale: string): string | null {
  return (locale === "ar" ? c.condition_ar : null) ?? c.condition ?? null;
}
