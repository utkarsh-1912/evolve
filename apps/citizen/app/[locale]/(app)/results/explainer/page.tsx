"use client";
// Result explainer (docs/09 §4.1-4, P-04): big locked number, comparison, DetectionBar, provenance, "Talk it through",
// questions notebook (on-device only). Own carrier_partner_only records only (P-06); every number via LockedNumber.
import { Button } from "@evolve/ui/primitives/button";
import { Card, CardHeader, VisibilityChip } from "@evolve/ui/primitives/display";
import { EmptyState, ErrorState, LoadingRegion, Notice, SimulatedBadge, Skeleton } from "@evolve/ui/primitives/feedback";
import { FormField, Textarea } from "@evolve/ui/primitives/field";
import { useToast } from "@evolve/ui/primitives/toast";
import { DetectionBar, LockedNumber, SourceCaption } from "@evolve/ui/risk/risk";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { FileSearch, MessagesSquare, Scale } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Link } from "@/i18n/navigation";
import { useVault } from "@/lib/queries";
import { useSession } from "@/lib/session";
import { conditionOf } from "@/lib/display";
import type { RiskOutput, VaultCall } from "@/lib/types";
import { CounselorHandoff } from "@/components/CounselorHandoff";
import { RequireSession } from "@/components/app-helpers";

export default function ExplainerPage() {
  const t = useTranslations("results");
  return (
    <RequireSession title={t("signInTitle")} body={t("signInBody")}>
      <ExplainerInner />
    </RequireSession>
  );
}

function ExplainerInner() {
  const t = useTranslations("explainer");
  const tc = useTranslations("compat");
  const tch = useTranslations("chrome");
  const locale = useLocale();
  const vault = useVault();
  const header = <PageHeader title={t("title")} description={t("lede")} badge={<SimulatedBadge label={tch("simulated")} />} />;
  if (vault.isLoading)
    return (
      <>
        {header}
        <LoadingRegion>
          <Skeleton className="h-80" rounded="lg" />
        </LoadingRegion>
      </>
    );
  if (vault.isError || !vault.data)
    return (
      <>
        {header}
        <ErrorState onRetry={() => vault.refetch()} reference="EXPLAINER-LOAD" />
      </>
    );
  const records = vault.data.records.filter((r) => r.audience === "carrier_partner_only" && r.status === "ok" && r.scenario === "discordant");
  return (
    <>
      {header}
      {records.length === 0 ? (
        <EmptyState
          icon={FileSearch}
          title={t("noneTitle")}
          body={t("none")}
          testId="results-none"
          action={
            <Button asChild variant="secondary">
              <Link href="/compatibility">{tch("nav.compatibility")}</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-8">
            {records.map((r) => (
              <Explainer key={r.digest} r={r} call={vault.data.calls.find((c) => c.hgnc_id === r.hgnc_id)} locale={locale} />
            ))}
            <p className="font-semibold">{tc("carrierNotDx")}</p>
            <Notice testId="judicial" icon={Scale}>
              {tc("judicial")}
            </Notice>
          </div>
          <aside className="space-y-4 lg:col-span-4">
            <Card>
              <CardHeader title={t("talk")} />
              <p className="text-sm">{tc("counselorBody")}</p>
              <Button asChild variant="secondary" className="mt-3" leadingIcon={<MessagesSquare aria-hidden />}>
                <Link href="/help#contact">{t("talk")}</Link>
              </Button>
            </Card>
            <QuestionsNotebook />
          </aside>
        </div>
      )}
    </>
  );
}

function Explainer({ r, call, locale }: { r: RiskOutput; call?: VaultCall; locale: string }) {
  const t = useTranslations("explainer");
  const tc = useTranslations("compat");
  const condition = (call && conditionOf(call, locale)) || r.gene;
  return (
    <article className="space-y-6" data-testid="explainer" aria-labelledby={`g-${r.hgnc_id}`}>
      <Card className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id={`g-${r.hgnc_id}`} className="text-lg font-semibold">
            {t("for", { condition })}
          </h2>
          <VisibilityChip visibility="only_you" />
        </div>
        <div className="grid gap-6 md:grid-cols-[1.2fr_1fr]">
          <div>
            <LockedNumber record={r} field="offspring_risk_one_in" size="giant" label={t("chanceLabel")} />
            <SourceCaption className="mt-2">{tc("source", { version: r.contract_version })}</SourceCaption>
          </div>
          <div className="grid content-start gap-3">
            <div className="rounded-lg bg-surface-2 p-4">
              {r.relative_to_unrelated_display ? (
                <LockedNumber record={r} field="relative_to_unrelated_display" size="large" label={t("relativeLabel")} provenance={false} />
              ) : (
                <p className="text-sm text-ink-2">{tc("relativeMissing")}</p>
              )}
            </div>
            <div className="rounded-lg bg-surface-2 p-4">
              <LockedNumber record={r} field="reference_unrelated_one_in" size="large" label={t("referenceLabel")} provenance={false} />
            </div>
          </div>
        </div>
      </Card>
      <Card className="space-y-4">
        <DetectionBar record={r} title={t("detectionTitle")} detectedLabel={t("detectionDetected")} missedLabel={t("detectionMissed")} />
        <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <p>
            {t("detectionRateLabel")}: <LockedNumber record={r} field="detection_rate" format="percent" provenance={false} />
          </p>
          <p>
            {t("partnerResidualLabel")}: <LockedNumber record={r} field="posterior_carrier_b_one_in" provenance={false} />
          </p>
        </div>
        <SourceCaption>{t("detectionCaption")}</SourceCaption>
        {r.F ? <p className="text-sm text-ink-2">{t("fNote")}</p> : null}
      </Card>
      {r.escalate ? <CounselorHandoff /> : null}
    </article>
  );
}

/** Questions notebook: stored only on this device (localStorage, per partner). Never sent (no free text to/through the backend). */
function QuestionsNotebook() {
  const t = useTranslations("explainer");
  const toast = useToast();
  const { session } = useSession();
  const key = `evolve.questions.${session?.partner_id ?? "anon"}`;
  const [text, setText] = useState(() => (typeof window === "undefined" ? "" : (window.localStorage.getItem(key) ?? "")));
  return (
    <Card>
      <CardHeader title={t("questionsTitle")} />
      <FormField label={t("questionsTitle")} hideLabel help={t("questionsHelp")}>
        <Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder={t("questionsPlaceholder")} rows={5} />
      </FormField>
      <Button
        variant="secondary"
        className="mt-3"
        onClick={() => {
          window.localStorage.setItem(key, text);
          toast({ title: t("questionsSaved"), tone: "success" });
        }}
      >
        {t("questionsSave")}
      </Button>
    </Card>
  );
}
