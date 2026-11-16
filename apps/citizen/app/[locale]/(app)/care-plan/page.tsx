"use client";
// Care plan (docs/09 §4.1-6 + §4.1-11 SURE): CareTimeline with timestamps/owner/next action (A4), tasks,
// appointments (SIMULATED), CareNavigator options as equal-weight cards (P-13; backend order is alphabetical,
// never a ranking), Thiqa eligibility checklist (own record only), SURE check (score < 4 escalates).
import { type LoopState } from "@evolve/ui/contracts";
import { CareTimeline } from "@evolve/ui/patterns/patterns";
import { Button } from "@evolve/ui/primitives/button";
import { Card, CardHeader, StatusChip, type Status } from "@evolve/ui/primitives/display";
import { Alert, EmptyState, ErrorState, LoadingRegion, SimulatedBadge, Skeleton } from "@evolve/ui/primitives/feedback";
import { SourceCaption } from "@evolve/ui/risk/risk";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { CalendarClock, ClipboardList, Hourglass } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Link } from "@/i18n/navigation";
import { useCarePlan, useSubmitSure } from "@/lib/queries";
import type { SureResult } from "@/lib/types";
import { RequireSession, useApiText, useFormat } from "@/components/app-helpers";

// Emerald means "Compatible" only (docs/03 §3), so a met check uses the neutral info signal.
const ELIG_TONE: Record<string, Status> = { met: "info", not_met: "neutral", needs_review: "review" };
const OWNER: Record<LoopState, "system" | "you" | "lab" | "counselor"> = {
  ResultIssued: "system",
  PatientNotified: "system",
  ComprehensionConfirmed: "you",
  ConfirmatoryDone: "lab",
  CounselingDone: "counselor",
  ReproReferralDone: "counselor",
  HumanClosure: "counselor",
};
const NEXT_HREF: Partial<Record<LoopState, string>> = { ResultIssued: "/results", PatientNotified: "/teachback", ComprehensionConfirmed: "/help#contact" };

export default function CarePlanPage() {
  const t = useTranslations("care");
  return (
    <RequireSession title={t("signInTitle")} body={t("signInBody")}>
      <CareInner />
    </RequireSession>
  );
}

function CareInner() {
  const t = useTranslations("care");
  const tc = useTranslations("chrome");
  const api = useApiText();
  const f = useFormat();
  const care = useCarePlan();
  const header = <PageHeader title={t("title")} description={t("description")} badge={<SimulatedBadge label={tc("simulated")} />} />;
  if (care.isLoading)
    return (
      <>
        {header}
        <LoadingRegion>
          <div className="grid gap-6 lg:grid-cols-12">
            <Skeleton className="h-96 lg:col-span-7" rounded="lg" />
            <Skeleton className="h-96 lg:col-span-5" rounded="lg" />
          </div>
        </LoadingRegion>
      </>
    );
  if (care.isError || !care.data)
    return (
      <>
        {header}
        <ErrorState onRetry={() => care.refetch()} reference="CARE-LOAD" />
      </>
    );
  const plan = care.data;
  const has = (k: string, ns: "task" | "taskStatus" | "eligibilityKey") => (t.has(`${ns}.${k}`) ? t(`${ns}.${k}`) : t(`${ns}.other`));

  return (
    <>
      {header}
      <div className="grid gap-6 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-7">
          <Card>
            <CardHeader title={t("timeline")} />
            {plan.loop.state ? (
              <CareTimeline
                label={t("timeline")}
                state={plan.loop.state}
                history={plan.loop.history}
                formatTs={f.dateTime}
                ownerFor={(s) => t(`owner.${OWNER[s]}`)}
                nextActionFor={(s) =>
                  NEXT_HREF[s] ? (
                    <Button asChild size="sm" variant="secondary">
                      <Link href={NEXT_HREF[s] as string}>{t(`next.${s}`)}</Link>
                    </Button>
                  ) : (
                    <span className="text-sm">{t(`next.${s}`)}</span>
                  )
                }
              />
            ) : (
              <EmptyState icon={Hourglass} title={t("timelineEmpty")} />
            )}
          </Card>

          <section aria-labelledby="options-h" className="space-y-3">
            <h2 id="options-h" className="text-lg font-semibold">
              {t("options")}
            </h2>
            <p className="text-sm text-ink-2">{t("optionsNote")}</p>
            <ul className="grid gap-3 sm:grid-cols-2" data-testid="care-options">
              {plan.options.map((o) => (
                <Card as="li" key={o.id} padding="sm" className="p-5">
                  <h3 className="font-semibold">{api(o.title_key)}</h3>
                  <p className="mt-1 text-sm text-ink-2">{api(o.body_key)}</p>
                </Card>
              ))}
            </ul>
          </section>
        </div>

        <div className="space-y-6 lg:col-span-5">
          <Card>
            <CardHeader title={t("tasks")} />
            {plan.tasks.length ? (
              <ul className="space-y-3" data-testid="care-tasks">
                {plan.tasks.map((k) => (
                  <li key={k.id} className="flex items-start justify-between gap-3 rounded-lg bg-surface-2 p-3">
                    <span className="flex items-start gap-2">
                      <ClipboardList aria-hidden className="mt-0.5 size-5 text-navy" />
                      <span>
                        <span className="block font-semibold">{has(k.kind, "task")}</span>
                        <span className="block text-sm text-ink-2">{t("due", { date: f.date(k.due) })}</span>
                      </span>
                    </span>
                    <StatusChip status="review" size="sm">
                      {has(k.status, "taskStatus")}
                    </StatusChip>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-ink-2">{t("tasksEmpty")}</p>
            )}
          </Card>

          <Card>
            <CardHeader title={t("appointments")} />
            {plan.appointments.length ? (
              <ul className="space-y-2">
                {plan.appointments.map((a) => (
                  <li key={a.id} className="flex items-center gap-2 text-sm">
                    <CalendarClock aria-hidden className="size-4 text-navy" />
                    {f.dateTime(a.ts)} · {t("appointmentWith", { role: a.with_role })}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-ink-2">{t("appointmentsEmpty")}</p>
            )}
          </Card>

          <Card>
            <CardHeader title={t("eligibility")} description={t("eligibilityNote")} />
            <ul className="divide-y divide-line" data-testid="eligibility">
              {plan.eligibility.checks.map((c) => (
                <li key={c.key} className="flex items-start justify-between gap-3 py-3">
                  <span>
                    <span className="block font-semibold">{has(c.key, "eligibilityKey")}</span>
                    <span className="block text-sm text-ink-2">{api(c.note_key)}</span>
                  </span>
                  <StatusChip status={ELIG_TONE[c.status] ?? "neutral"} size="sm">
                    {t(`eligibilityStatus.${c.status}`)}
                  </StatusChip>
                </li>
              ))}
            </ul>
          </Card>

          {plan.loop.state ? <SureCheck /> : null}
        </div>
      </div>
    </>
  );
}

/** SURE (4 yes/no). No default answers; score < 4 escalates to a counselor (backend), said kindly. */
function SureCheck() {
  const t = useTranslations("sure");
  const submit = useSubmitSure();
  const [answers, setAnswers] = useState<(boolean | undefined)[]>([undefined, undefined, undefined, undefined]);
  const [done, setDone] = useState<SureResult | null>(null);
  const items = t.raw("items") as string[];
  return (
    <Card data-testid="sure">
      <CardHeader title={t("title")} description={t("description")} />
      {done ? (
        <Alert tone={done.escalated ? "info" : "success"} testId="sure-done">
          {done.escalated ? t("followUp") : t("allYes")}
        </Alert>
      ) : (
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            submit.mutate(answers as boolean[], { onSuccess: setDone });
          }}
        >
          {items.map((q, i) => (
            <fieldset key={i} className="space-y-2">
              <legend className="text-sm font-semibold">{q}</legend>
              <div className="flex gap-2">
                {[true, false].map((v) => (
                  <label
                    key={String(v)}
                    className={`inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-md border px-4 text-sm font-semibold has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-navy has-[:focus-visible]:ring-offset-2 ${answers[i] === v ? "border-navy bg-navy text-cream" : "border-line-strong bg-surface-1 text-ink"}`}
                  >
                    <input
                      type="radio"
                      name={`sure-${i}`}
                      className="sr-only"
                      checked={answers[i] === v}
                      onChange={() => setAnswers((a) => a.map((x, k) => (k === i ? v : x)))}
                    />
                    {v ? t("yes") : t("no")}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          {submit.isError ? <ErrorState reference="SURE-SUBMIT" /> : null}
          <Button type="submit" disabled={answers.some((a) => a === undefined)} loading={submit.isPending} data-testid="sure-submit">
            {t("submit")}
          </Button>
          <SourceCaption>{t("source")}</SourceCaption>
        </form>
      )}
    </Card>
  );
}
