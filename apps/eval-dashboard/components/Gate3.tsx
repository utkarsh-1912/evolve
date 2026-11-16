"use client";
// Gate-3 app suites as recorded in the evidence pack (`gate3`, NOTE-EVIDENCE-SCHEMA 2026-11-16), incl. what was
// NOT covered. Rendered only when the pack carries the field.
import { StatusChip } from "@evolve/ui";
import { useLocale, useTranslations } from "next-intl";
import { evidence } from "@/lib/evidence";
import { count } from "@/lib/format";

const td = "px-4 py-2.5 align-top";

export function Gate3() {
  const t = useTranslations("gate3");
  const locale = useLocale();
  const g = evidence.gate3;
  if (!g) return null;
  return (
    <div className="mt-8 space-y-3" data-testid="gate3">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-base font-semibold text-ink">{t("title", { date: g.date })}</h3>
        <StatusChip status={g.passed ? "compatible" : "escalated"} size="sm">
          {g.passed ? t("passed") : t("failed")}
        </StatusChip>
        <span className="font-mono text-sm text-ink-2">{t("p0", { n: count(g.p0, locale) })}</span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-line bg-surface-1">
        <table className="w-full text-sm">
          <caption className="sr-only">{t("title", { date: g.date })}</caption>
          <thead>
            <tr className="border-b border-line-strong text-xs uppercase tracking-[0.06em] text-ink-2">
              <th scope="col" className="px-4 py-3 text-start font-semibold">{t("app")}</th>
              <th scope="col" className="px-4 py-3 text-start font-semibold">{t("config")}</th>
              <th scope="col" className="px-4 py-3 text-start font-semibold">{t("passedCol")}</th>
              <th scope="col" className="px-4 py-3 text-start font-semibold">{t("failedCol")}</th>
            </tr>
          </thead>
          <tbody>
            {g.suites.map((s, i) => (
              <tr key={i} className="border-b border-line last:border-b-0">
                <th scope="row" className={`${td} text-start font-mono font-normal text-ink`}>{s.app}</th>
                <td className={`${td} text-ink-2`}>{s.config}</td>
                <td className={`${td} font-mono`} dir="ltr">{count(s.passed, locale)}</td>
                <td className={`${td} font-mono ${s.failed > 0 ? "font-semibold text-escalated-ink" : ""}`} dir="ltr">{count(s.failed, locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {g.not_covered.length ? (
        <p className="text-sm text-ink" data-testid="gate3-not-covered">
          <span className="font-semibold">{t("notCovered")}:</span> {g.not_covered.join(" · ")}
        </p>
      ) : null}
      <p className="text-xs text-ink-2">{t("source", { source: g.source })}</p>
    </div>
  );
}
