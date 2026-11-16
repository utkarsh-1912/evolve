"use client";
// Teach-back (docs/09 §4.1-5): one statement per screen, progress, kind feedback, never "fail" wording.
// Not all correct => the backend escalates to a counselor (trigger d); we say so plainly, without judgement.
import { Button } from "@evolve/ui/primitives/button";
import { Card } from "@evolve/ui/primitives/display";
import { Alert, EmptyState, ErrorState, LoadingRegion, SimulatedBadge, Skeleton } from "@evolve/ui/primitives/feedback";
import { RadioGroup } from "@evolve/ui/primitives/radio-group";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { ArrowLeft, ArrowRight, Hourglass, ListChecks } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Link } from "@/i18n/navigation";
import { useCarePlan, useSubmitTeachback, useTeachbackStart } from "@/lib/queries";
import type { TeachbackResult } from "@/lib/types";
import { RequireSession, useApiText } from "@/components/app-helpers";

export default function TeachbackPage() {
  const t = useTranslations("teachback");
  return (
    <RequireSession title={t("signInTitle")} body={t("signInBody")}>
      <TeachbackInner />
    </RequireSession>
  );
}

function TeachbackInner() {
  const t = useTranslations("teachback");
  const tc = useTranslations("chrome");
  const api = useApiText();
  const start = useTeachbackStart();
  const care = useCarePlan();
  const submit = useSubmitTeachback();
  const [i, setI] = useState(0);
  const [answers, setAnswers] = useState<(boolean | undefined)[]>([]);
  const [result, setResult] = useState<TeachbackResult | null>(null);
  const header = <PageHeader title={t("title")} description={t("description")} badge={<SimulatedBadge label={tc("simulated")} />} />;

  if (start.isLoading || care.isLoading)
    return (
      <>
        {header}
        <LoadingRegion>
          <Skeleton className="h-64 max-w-2xl" rounded="lg" />
        </LoadingRegion>
      </>
    );
  if (start.isError || !start.data)
    return (
      <>
        {header}
        <ErrorState onRetry={() => start.refetch()} reference="TEACHBACK-LOAD" />
      </>
    );
  if (!care.data?.loop.state)
    return (
      <>
        {header}
        <EmptyState
          icon={Hourglass}
          title={t("notReadyTitle")}
          body={t("notReadyBody")}
          action={
            <Button asChild variant="secondary">
              <Link href="/compatibility">{tc("nav.compatibility")}</Link>
            </Button>
          }
        />
      </>
    );

  const qs = start.data.questions;
  const q = qs[i];

  if (result) {
    return (
      <>
        {header}
        <Card className="max-w-2xl space-y-5" data-testid="teachback-done" data-passed={result.passed}>
          <h2 className="text-xl font-semibold">{t("doneTitle")}</h2>
          <Alert tone={result.passed ? "success" : "info"}>{result.passed ? t("passedBody") : t("notYetBody")}</Alert>
          <section>
            <h3 className="mb-2 flex items-center gap-2 font-semibold">
              <ListChecks aria-hidden className="size-5 text-navy" />
              {t("review")}
            </h3>
            <ul className="list-disc space-y-1 ps-5">
              {qs.map((x) => (
                <li key={x.id}>{t.has(`explain.${x.id}`) ? t(`explain.${x.id}`) : api(x.key)}</li>
              ))}
            </ul>
          </section>
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link href="/care-plan">{t("toCare")}</Link>
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setResult(null);
                setAnswers([]);
                setI(0);
              }}
            >
              {t("again")}
            </Button>
          </div>
        </Card>
      </>
    );
  }

  const value = answers[i] === undefined ? undefined : answers[i] ? "true" : "false";
  const last = i === qs.length - 1;
  return (
    <>
      {header}
      <Card className="max-w-2xl space-y-6" data-testid="teachback-question">
        <div>
          <p className="text-sm font-semibold text-ink-2" aria-live="polite">
            {t("progress", { n: i + 1, total: qs.length })}
          </p>
          <div className="mt-2 flex gap-1.5" aria-hidden>
            {qs.map((x, k) => (
              <span key={x.id} className={`h-1.5 flex-1 rounded-full ${k <= i ? "bg-navy" : "bg-surface-2"}`} />
            ))}
          </div>
        </div>
        <p className="text-xl font-semibold leading-snug" data-testid="teachback-statement">
          {api(q.key) !== q.key ? api(q.key) : q.statement}
        </p>
        <RadioGroup
          key={q.id}
          legend={t("question")}
          orientation="horizontal"
          value={value}
          onValueChange={(v) => setAnswers((a) => Object.assign([...a], { [i]: v === "true" }))}
          options={[
            { value: "true", label: t("agree") },
            { value: "false", label: t("disagree") },
          ]}
        />
        {submit.isError ? <ErrorState reference="TEACHBACK-SUBMIT" onRetry={() => submit.reset()} /> : null}
        <div className="flex flex-wrap justify-between gap-3">
          <Button variant="ghost" disabled={i === 0} onClick={() => setI(i - 1)} leadingIcon={<ArrowLeft aria-hidden className="rtl:-scale-x-100" />}>
            {t("back")}
          </Button>
          {last ? (
            <Button
              data-testid="teachback-submit"
              disabled={answers.length !== qs.length || answers.some((a) => a === undefined)}
              loading={submit.isPending}
              onClick={() => submit.mutate(answers as boolean[], { onSuccess: setResult })}
            >
              {t("submit")}
            </Button>
          ) : (
            <Button data-testid="teachback-next" disabled={value === undefined} onClick={() => setI(i + 1)} trailingIcon={<ArrowRight aria-hidden className="rtl:-scale-x-100" />}>
              {t("next")}
            </Button>
          )}
        </div>
      </Card>
    </>
  );
}
