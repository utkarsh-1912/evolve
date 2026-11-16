"use client";
// Consultation Brief (R-AGT-3, docs/09 §4.2): trigger, family structure, consented variant summary (figures come from
// the full locked record with the same digest), pending tasks, couple questions, teach-back / SURE status.
import { Alert, Card, CardHeader, LockedNumber, StatusChip } from "@evolve/ui";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import type { CaseView, RiskOutput } from "@/lib/types";
import { isOutside } from "@/lib/types";
import { OutsideConsent, TriggerChip } from "../Workbench";

export function useRelationshipLabel() {
  const t = useTranslations("relationship");
  return (r: string) => (t.has(r as "unrelated") ? t(r as "unrelated") : r.replace(/_/g, " "));
}

export function BriefTab({ view, onOpenVariants, aiPanel }: { view: CaseView; onOpenVariants: () => void; aiPanel?: ReactNode }) {
  const t = useTranslations("brief");
  const tt = useTranslations("triggers");
  const tv = useTranslations("variants");
  const rel = useRelationshipLabel();
  const b = view.brief;
  const records = view.variants.filter((v): v is RiskOutput => !isOutside(v));
  const recordFor = (digest: string) => records.find((r) => r.digest === digest);

  return (
    <div className="grid gap-5 xl:grid-cols-2" data-testid="brief">
      <Card className="xl:col-span-2">
        <CardHeader title={t("trigger")} level={2} actions={<TriggerChip trigger={b.trigger} size="md" />} />
        <p className="max-w-[72ch] text-ink">{tt(`explain.${b.trigger}`)}</p>
        <p className="mt-3 text-sm text-ink-2">{b.note}</p>
      </Card>

      {aiPanel}

      {b.consent_revoked_data_purged ? (
        <Alert tone="warning" className="xl:col-span-2">
          {t("purged")}
        </Alert>
      ) : null}

      <Card>
        <CardHeader title={t("variants")} level={2} />
        {b.variant_summary.length === 0 ? (
          <p className="text-sm text-ink-2">{tv("empty")}</p>
        ) : (
          <ul className="space-y-3">
            {b.variant_summary.map((v, i) => {
              if (isOutside(v)) return <li key={`o-${i}`}><OutsideConsent /></li>;
              const full = recordFor(v.digest);
              return (
                <li key={v.digest} className="rounded-lg border border-line p-3" data-testid="brief-variant">
                  <p className="font-semibold">
                    <span className="font-mono" dir="ltr">
                      {v.gene}
                    </span>{" "}
                    · {tv(`scenarios.${v.scenario}`)}
                  </p>
                  <p className="text-sm text-ink-2">
                    {tv(`audiences.${v.audience}`)} · {v.status === "ok" ? tv("statuses.ok") : tv("statuses.needs_counselor")}
                    {v.escalate ? ` · ${tv("escalateYes")}` : ""}
                  </p>
                  {full ? (
                    <div className="mt-2">
                      <LockedNumber record={full} field="offspring_risk_one_in" label={tv("offspring")} provenance={false} />
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
        <button type="button" onClick={onOpenVariants} className="mt-3 min-h-11 text-sm font-semibold text-ink underline underline-offset-4">
          {t("openVariants")}
        </button>
      </Card>

      <Card>
        <CardHeader title={t("pedigree")} level={2} />
        {b.pedigree ? (
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
            <dt className="text-ink-2">{t("relationship")}</dt>
            <dd>{rel(b.pedigree.relationship)}</dd>
            <dt className="text-ink-2">{t("wrightPaths")}</dt>
            <dd className="font-mono">{b.pedigree.wright_paths}</dd>
            <dt className="text-ink-2">{t("familyHistory")}</dt>
            <dd>
              {b.pedigree.family_history.length ? (
                <ul className="list-disc ps-5">
                  {b.pedigree.family_history.map((f, i) => (
                    <li key={i}>
                      {f.finding}
                      {f.hpo ? <span className="font-mono text-xs text-ink-2"> ({f.hpo})</span> : null}
                    </li>
                  ))}
                </ul>
              ) : (
                t("noFamilyHistory")
              )}
            </dd>
          </dl>
        ) : (
          <p className="text-sm text-ink-2">{t("purged")}</p>
        )}
      </Card>

      <Card>
        <CardHeader title={t("comprehension")} level={2} />
        <ul className="space-y-2 text-sm" data-testid="comprehension">
          {Object.entries(b.comprehension).map(([pid, c]) => (
            <li key={pid} className="flex flex-wrap items-center gap-2">
              <span className="w-14 font-mono font-semibold" dir="ltr">
                {pid}
              </span>
              <span className="text-ink-2">{t("teachback")}:</span>
              {c.teachback ? (
                <StatusChip status={c.teachback.passed ? "compatible" : "review"} size="sm">
                  {c.teachback.passed ? t("passed", { score: c.teachback.score }) : t("notPassed", { score: c.teachback.score })}
                </StatusChip>
              ) : (
                <span>{t("notTaken")}</span>
              )}
              <span className="text-ink-2">· {t("sure")}:</span>
              {c.sure ? <span className="font-mono">{t("sureScore", { score: c.sure.score })}</span> : <span>{t("notTaken")}</span>}
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <CardHeader title={t("pendingTasks")} level={2} />
        {b.pending_tasks.length ? (
          <ul className="space-y-2 text-sm">
            {b.pending_tasks.map((p, i) => (
              <li key={i} className="rounded-md bg-surface-2 p-3">
                <p className="font-semibold">{p.code}</p>
                <p className="text-ink-2">
                  <span className="font-mono" dir="ltr">
                    {p.for}
                  </span>{" "}
                  · {p.description}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-ink-2">{t("noPendingTasks")}</p>
        )}
        <h3 className="mt-5 font-semibold text-ink">{t("questions")}</h3>
        {b.couple_questions.length ? (
          <ul className="list-disc ps-5 text-sm">
            {b.couple_questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-ink-2">{t("noQuestions")}</p>
        )}
      </Card>
    </div>
  );
}
