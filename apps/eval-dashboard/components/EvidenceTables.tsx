"use client";
// Evidence tables: simulated-vs-real, safety gate (v1 vs held-out, G2 per DECISIONS #37), leakage counter + proof
// table, and the per-suite test matrix. All rows/values are read from the evidence pack.
import { Card, StatusChip } from "@evolve/ui";
import { FlaskConical, Gauge, HelpCircle } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { evidence, gateTarget, holdoutSets } from "@/lib/evidence";
import { count, pct, pctTarget } from "@/lib/format";

function Table({ caption, head, children, testId }: { caption: string; head: ReactNode[]; children: ReactNode; testId?: string }) {
  return (
    <div tabIndex={0} role="region" aria-label={caption} className="overflow-x-auto rounded-lg border border-line bg-surface-1">
      <table className="w-full text-sm" data-testid={testId}>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-line-strong">
            {head.map((h, i) => (
              <th key={i} scope="col" className="px-4 py-3 text-start text-xs font-semibold uppercase tracking-[0.06em] text-ink-2">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

const td = "px-4 py-2.5 align-top";

export function SimVsRealTable() {
  const t = useTranslations("simreal");
  return (
    <div className="space-y-2">
      <Table caption={t("title")} head={[t("item"), t("source"), t("status")]} testId="simreal-table">
        {evidence.simulated_vs_real.map((r) => (
          <tr key={r.item} className="border-b border-line last:border-b-0" data-row-simulated={String(r.simulated)}>
            <th scope="row" className={`${td} text-start font-semibold text-ink`}>
              {r.item}
            </th>
            <td className={`${td} text-ink-2`}>{r.source}</td>
            <td className={td}>
              {r.simulated === true ? (
                <StatusChip status="review" icon={FlaskConical} size="sm">
                  {t("simulated")}
                </StatusChip>
              ) : r.simulated === false ? (
                <StatusChip status="info" icon={Gauge} size="sm">
                  {t("real")}
                </StatusChip>
              ) : (
                <StatusChip status="neutral" icon={HelpCircle} size="sm">
                  {t("notInstrumented")}
                </StatusChip>
              )}
            </td>
          </tr>
        ))}
      </Table>
      <p className="text-xs text-ink-2">{t("caption")}</p>
    </div>
  );
}

export function GatePanel() {
  const t = useTranslations("gate");
  const locale = useLocale();
  const sets = holdoutSets();
  const target = gateTarget();
  const g2 = evidence.g2;
  const redteam = Object.entries(evidence.redteam);
  // Category table: the current held-out set (last key containing "holdout"), as measured.
  const current = [...redteam].reverse().find(([k]) => k.includes("holdout")) ?? redteam[redteam.length - 1];
  const cats = current ? Object.entries(current[1].categories) : [];
  const yesNo = (b: boolean) => (b ? t("yes") : t("no"));
  const label = (ns: "setName" | "setKey", key: string) => (t.has(`${ns}.${key}`) ? t(`${ns}.${key}` as "setName.holdout") : key);
  const flags: [string, boolean | undefined][] = [
    [t("twoSets"), g2.two_sets_meet_target],
    [t("marker"), g2.holdout_pass_marker_exists],
    [t("llm"), g2.llm_paraphrase_may_be_enabled ?? g2.c_holdout?.llm_paraphrase_may_be_enabled],
    [t("blocksG2"), g2.blocks_g2 ?? g2.c_holdout?.blocks_g2],
  ];
  return (
    <div className="space-y-6">
      <p className="max-w-[80ch] rounded-lg border border-line bg-surface-2 p-4 text-sm font-medium text-ink" data-testid="closed-templates">
        {t("closedTemplates")}
      </p>
      <div className="grid gap-6 xl:grid-cols-12">
        <Card variant="raised" className="space-y-5 xl:col-span-6" data-testid="g2-panel">
          <h3 className="text-base font-semibold text-ink">{t("sets")}</h3>
          <ul className="space-y-5">
            {sets.map((s) => (
              <li key={s.name} className="border-t border-line pt-4 first:border-t-0 first:pt-0" data-testid="holdout-set" data-meets={s.meets_target}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-semibold text-ink">{label("setName", s.name)}</p>
                  <StatusChip status={s.meets_target ? "compatible" : "escalated"} size="sm">
                    {t("verdict")}: {yesNo(s.meets_target)}
                  </StatusChip>
                </div>
                {s.measured ? (
                  <p className="text-xs text-ink-2">
                    {t("measured")}: {s.measured}
                  </p>
                ) : null}
                <div className="mt-3 grid grid-cols-2 gap-6">
                  <div>
                    <p className="text-sm text-ink-2">{t("caught")}</p>
                    <p className="font-display text-5xl font-light leading-none tracking-tight text-ink" dir="ltr" data-testid="set-catch">
                      {pct(s.catch, locale)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-ink-2">{t("fp")}</p>
                    <p className="font-display text-5xl font-light leading-none tracking-tight text-ink" dir="ltr" data-testid="set-fp">
                      {pct(s.fp, locale)}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
          {target ? (
            <p className="font-mono text-sm text-ink" dir="ltr">
              {t("target", { catchMin: pctTarget(target.catch_min, locale), fpMax: pctTarget(target.fp_max, locale) })}
            </p>
          ) : null}
          <dl className="grid gap-2 text-sm">
            {flags
              .filter(([, v]) => v !== undefined)
              .map(([k, v]) => (
                <div key={k} className="flex items-center justify-between gap-4">
                  <dt className="text-ink-2">{k}</dt>
                  <dd className="font-semibold text-ink">{yesNo(!!v)}</dd>
                </div>
              ))}
          </dl>
          <p className="text-xs text-ink-2">{g2.decision}</p>
        </Card>

        <div className="space-y-6 xl:col-span-6">
          <Table caption={t("corpus")} head={[t("set"), t("caught"), t("fp")]} testId="redteam-sets">
            {redteam.map(([k, s]) => (
              <tr key={k} className="border-b border-line last:border-b-0">
                <th scope="row" className={`${td} text-start font-semibold text-ink`}>
                  {label("setKey", k)}
                </th>
                <td className={`${td} font-mono`} dir="ltr">
                  {count(s.adversarial.intercepted, locale)}/{count(s.adversarial.n, locale)} = {pct(s.adversarial.rate, locale)}
                </td>
                <td className={`${td} font-mono`} dir="ltr">
                  {count(s.benign.false_positives, locale)}/{count(s.benign.n, locale)} = {pct(s.benign.fp_rate, locale)}
                </td>
              </tr>
            ))}
          </Table>
          {current ? (
            <div>
              <h3 className="mb-2 text-base font-semibold text-ink">
                {t("categories")} · {label("setKey", current[0])}
              </h3>
              <Table caption={t("categories")} head={[t("category"), t("n"), t("rate"), t("lang")]} testId="holdout-categories">
                {cats.map(([k, c]) => (
                  <tr key={k} className="border-b border-line last:border-b-0">
                    <th scope="row" className={`${td} text-start font-normal text-ink`}>
                      {t.has(`cat.${k}`) ? t(`cat.${k}` as "cat.directive") : k}
                    </th>
                    <td className={`${td} font-mono`} dir="ltr">
                      {count(c.n, locale)}
                    </td>
                    <td className={`${td} font-mono`} dir="ltr">
                      {count(c.ok, locale)} · {pct(c.pass_rate, locale)}
                    </td>
                    <td className={`${td} font-mono text-ink-2`} dir="ltr">
                      {c.en} / {c.ar}
                    </td>
                  </tr>
                ))}
              </Table>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function LeakagePanel() {
  const t = useTranslations("leak");
  const locale = useLocale();
  const pr = evidence.dimensions.privacy;
  return (
    <div className="grid gap-6 xl:grid-cols-12">
      <div className="xl:col-span-5">
        <p className="text-sm font-semibold uppercase tracking-[0.08em] text-ink-2">{t("title")}</p>
        <p
          className="font-display text-[clamp(8rem,18vw,16rem)] font-light leading-[0.85] tracking-tighter text-ink"
          dir="ltr"
          data-testid="leak-counter"
        >
          {count(pr.live_leaks, locale)}
        </p>
        <p className="mt-2 font-mono text-base text-ink">{t("of", { n: count(pr.live_responses_scanned, locale) })}</p>
        <div className="mt-6 rounded-lg border border-escalated/60 bg-escalated/10 p-4 text-sm text-ink" data-testid="leak-honest">
          {t("honest", { k: count(pr.redteam_leaks, locale) })}
        </div>
      </div>
      <div className="space-y-2 xl:col-span-7">
        <h3 className="text-base font-semibold text-ink">{t("proof")}</h3>
        <Table caption={t("proof")} head={[t("category"), t("n"), t("intercepted"), t("leaks")]} testId="leak-proof">
          {pr.table.map((r) => (
            <tr key={r.category} className="border-b border-line last:border-b-0">
              <th scope="row" className={`${td} text-start font-mono font-normal text-ink`}>
                {r.category}
              </th>
              <td className={`${td} font-mono`} dir="ltr">
                {count(r.n, locale)}
              </td>
              <td className={`${td} font-mono`} dir="ltr">
                {count(r.intercepted.k, locale)} · {pct(r.intercepted.value, locale)}
              </td>
              <td className={`${td} font-mono ${r.leaks.k > 0 ? "font-semibold text-escalated-ink" : ""}`} dir="ltr">
                {count(r.leaks.k, locale)}
              </td>
            </tr>
          ))}
        </Table>
      </div>
    </div>
  );
}

export function TestMatrix() {
  const t = useTranslations("tests");
  const locale = useLocale();
  const suites = Object.entries(evidence.tests);
  return (
    <div className="space-y-3">
      <Table caption={t("title")} head={[t("suite"), t("tests"), t("passed"), t("failed"), t("status")]} testId="test-matrix">
        {suites.map(([name, s]) => (
          <tr key={name} className="border-b border-line last:border-b-0" data-status={s.status}>
            <th scope="row" className={`${td} text-start font-mono font-normal text-ink`}>
              {name}
            </th>
            <td className={`${td} font-mono`} dir="ltr">
              {count(s.tests, locale)}
            </td>
            <td className={`${td} font-mono`} dir="ltr">
              {count(s.passed, locale)}
            </td>
            <td className={`${td} font-mono ${s.failed + s.errors > 0 ? "font-semibold text-escalated-ink" : ""}`} dir="ltr">
              {count(s.failed + s.errors, locale)}
            </td>
            <td className={td}>
              <StatusChip status={s.status === "green" ? "compatible" : "escalated"} size="sm">
                {s.status === "green" ? t("green") : t("red")}
              </StatusChip>
            </td>
          </tr>
        ))}
      </Table>
      <p className="flex items-center gap-2 text-sm text-ink">
        <span className="font-mono">{t("guardrail")}</span>
        <StatusChip status={evidence.guardrail_check.ok ? "compatible" : "escalated"} size="sm">
          {evidence.guardrail_check.ok ? t("ok") : `${t("fail")}: ${evidence.guardrail_check.violations.length}`}
        </StatusChip>
      </p>
    </div>
  );
}
