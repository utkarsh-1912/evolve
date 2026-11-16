"use client";
// Compatibility (R-UX-1; R-PRIV-1/2 surface) inside the shell. Two columns: the check/result (primary) and a
// "Sharing & consent" panel (who consented, when, expiry, withdraw with ConfirmDialog; A6). On mobile the panel
// sits below the result. Only the APSI result and couple-audience records are shown (P-06).
// api.md v1.2.1: when review_required is true the headline is "Counselor review", never "Compatible".
import { MessageThread } from "@evolve/ui/patterns/patterns";
import { Button } from "@evolve/ui/primitives/button";
import { Card, CardHeader, StatusChip } from "@evolve/ui/primitives/display";
import { Alert, ErrorState, LoadingRegion, Notice, SimulatedBadge, Skeleton } from "@evolve/ui/primitives/feedback";
import { Switch } from "@evolve/ui/primitives/switch";
import { Stepper, type StepState } from "@evolve/ui/primitives/stepper";
import { ConfirmDialog } from "@evolve/ui/primitives/dialog";
import { useToast } from "@evolve/ui/primitives/toast";
import { OverlapCircles } from "@evolve/ui/risk/motion";
import { IconArray, LockedNumber, SourceCaption } from "@evolve/ui/risk/risk";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { FlaskConical, Scale } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { CounselorHandoff } from "@/components/CounselorHandoff";
import { OptionCards } from "@/components/OptionCards";
import { SignInRequired } from "@/components/SignInRequired";
import { useFormatTs } from "@/components/CitizenShell";
import { useCompatibility, useCompatResult, useConsents, useGrantConsent, useHome, useRevokeConsent, useSimulatePartnerConsent } from "@/lib/queries";
import { withoutPageNotices } from "@/lib/display";
import { CounselorRail } from "@/components/app-helpers";
import { counterpartFor, useSession } from "@/lib/session";
import type { CompatibilityResponse, Consent } from "@/lib/types";
import { ApiError } from "@/lib/types";

const reducedMotion = () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const isActive = (c: Consent) => c.status === "active" && c.period.end > new Date().toISOString();

export default function CompatibilityPage() {
  const t = useTranslations("compat");
  const tc = useTranslations("chrome");
  const toast = useToast();
  const formatTs = useFormatTs();
  const { session, ready } = useSession();
  const consents = useConsents();
  const grant = useGrantConsent();
  const revoke = useRevokeConsent();
  const simulate = useSimulatePartnerConsent();
  const check = useCompatibility();
  const cached = useCompatResult();
  const home = useHome();
  const [animating, setAnimating] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [notice, setNotice] = useState<"needBoth" | "revoked" | "error" | "consentError" | null>(null);

  if (ready && !session) return <SignInRequired title={t("signInTitle")} body={t("signInBody")} />;
  if (!session) return null;

  const me = session.partner_id;
  const partner = counterpartFor(me);
  const list = consents.data ?? [];
  const mine = list.find((c) => c.patient === me && c.counterpart === partner && isActive(c));
  const theirs = list.find((c) => c.patient === partner && c.counterpart === me && isActive(c));
  const result = check.data ?? cached.data ?? null;
  const resultReadyElsewhere = !result && home.data?.couple_status === "result_ready";
  const running = animating || check.isPending;

  const steps: { label: string; state: StepState }[] = [
    { label: t("step1"), state: mine ? "complete" : "current" },
    { label: t("step2"), state: mine && theirs ? "complete" : mine ? "current" : "upcoming" },
    { label: t("step3"), state: result ? "complete" : mine && theirs ? "current" : "upcoming" },
  ];

  async function onToggle(on: boolean) {
    setNotice(null);
    if (!on) return setConfirmOpen(true);
    try {
      await grant.mutateAsync();
      toast({ title: t("consentGiven"), tone: "success" });
    } catch {
      setNotice("consentError");
    }
  }

  async function onRevoke() {
    if (!mine) return;
    try {
      await revoke.mutateAsync(mine.id);
      check.reset();
      setNotice("revoked");
      toast({ title: t("revoked"), tone: "info" });
    } catch {
      setNotice("consentError");
    }
  }

  async function run() {
    setNotice(null);
    setAnimating(true);
    const minAnim = new Promise((r) => setTimeout(r, reducedMotion() ? 0 : 1200));
    try {
      await Promise.all([check.mutateAsync(), minAnim]);
    } catch (e) {
      setNotice(e instanceof ApiError && e.status === 409 ? "needBoth" : "error");
    } finally {
      setAnimating(false);
    }
  }

  return (
    <>
      <PageHeader title={t("title")} description={t("lede")} badge={<SimulatedBadge label={tc("simulated")} />} />
      <div className="mb-6">
        <Stepper label={t("stepper")} steps={steps} />
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-8">
          {consents.isLoading ? (
            <LoadingRegion>
              <Skeleton className="h-72" rounded="lg" />
            </LoadingRegion>
          ) : consents.isError ? (
            <ErrorState onRetry={() => consents.refetch()} reference="CONSENTS-LOAD" />
          ) : result ? (
            <Result result={result} />
          ) : (
            <Card className="space-y-5">
              <Switch
                data-testid="consent-toggle"
                checked={!!mine}
                onCheckedChange={onToggle}
                disabled={grant.isPending || revoke.isPending || running}
                label={t("myConsent")}
                help={t("myConsentHelp")}
              />
              <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
                <span className="text-sm text-ink-2">{t("partnerStatus")}:</span>
                {theirs ? (
                  <StatusChip status="info" size="sm">
                    {t("partnerAgreed")}
                  </StatusChip>
                ) : (
                  <>
                    <StatusChip status="review" size="sm">
                      {t("partnerWaiting")}
                    </StatusChip>
                    <Button
                      variant="secondary"
                      size="sm"
                      data-testid="simulate-partner"
                      disabled={!mine}
                      loading={simulate.isPending}
                      leadingIcon={<FlaskConical aria-hidden />}
                      onClick={() => simulate.mutate(undefined, { onError: () => setNotice("consentError") })}
                    >
                      {t("simulatePartner")}
                    </Button>
                  </>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-4">
                <Button data-testid="run-check" size="lg" disabled={!mine || !theirs || running} loading={running} onClick={run}>
                  {running ? t("running") : resultReadyElsewhere ? t("rerun") : t("run")}
                </Button>
              </div>
              {notice && notice !== "revoked" ? (
                <Alert tone={notice === "needBoth" ? "warning" : "danger"} testId="notice">
                  {t(notice)}
                </Alert>
              ) : null}
              <div className="flex justify-center" aria-live="polite">
                <OverlapCircles phase={running ? "running" : "idle"} label={running ? t("running") : t("step3")} />
              </div>
            </Card>
          )}
        </div>

        <aside className="space-y-4 lg:col-span-4">
          <Card aria-labelledby="sharing-h" data-testid="revoke-panel">
            <CardHeader id="sharing-h" title={t("sharingTitle")} />
            <dl className="space-y-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                <dt className="text-ink-2">{t("sharingYou")}</dt>
                <dd className="flex flex-col items-end gap-1">
                  <StatusChip status={mine ? "info" : "neutral"} size="sm">
                    {mine ? t("given") : t("notGiven")}
                  </StatusChip>
                  {mine ? <span className="text-ink-2">{t("expires", { time: formatTs(mine.period.end) })}</span> : null}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-ink-2">{t("sharingPartner")}</dt>
                <dd>
                  <StatusChip status={theirs ? "info" : "neutral"} size="sm">
                    {theirs ? t("given") : t("notGiven")}
                  </StatusChip>
                </dd>
              </div>
            </dl>
            <div className="mt-5 border-t border-line pt-4">
              {mine ? (
                <ConfirmDialog
                  open={confirmOpen}
                  onOpenChange={setConfirmOpen}
                  testId="revoke-dialog"
                  trigger={
                    <Button variant="danger-outline" block data-testid="revoke">
                      {t("revoke")}
                    </Button>
                  }
                  title={t("revokeTitle")}
                  description={t("revokeDescription")}
                  consequences={t.raw("revokeConsequences") as string[]}
                  confirmLabel={t("revokeConfirm")}
                  onConfirm={onRevoke}
                />
              ) : (
                <p className="text-sm text-ink" data-testid="revoke-none">
                  {t("revokeNone")}
                </p>
              )}
              {notice === "revoked" ? (
                <p role="status" className="mt-3 text-sm font-medium text-ink">
                  {t("revoked")}
                </p>
              ) : null}
            </div>
          </Card>
          <CounselorRail />
        </aside>
      </div>
    </>
  );
}

function Result({ result }: { result: CompatibilityResponse }) {
  const t = useTranslations("compat");
  const formatTs = useFormatTs();
  const { apsi, records, messages, review_required } = result;
  // Only records whose gene is in the consented APSI intersection may be shown to the couple (P-06).
  const shared = records.filter((r) => r.audience === "couple" && apsi.shared_hgnc_ids.includes(r.hgnc_id));
  const escalated = messages.some((m) => m.kind === "escalation");
  const thread = (
    <Card>
      <CardHeader title={t("messagesTitle")} />
      <MessageThread
        title={t("messagesTitle")}
        formatTs={formatTs}
        messages={messages
          .filter((m) => m.kind === "result" || m.kind === "escalation")
          // Display-only: the judicial + decision-support sentences are already on this page (REQUEST-UI-CIT-1).
          .map((m) => ({ id: m.id, kind: m.kind, text: withoutPageNotices(m.text), gatePassed: m.gate.passed, author: t("assistant") }))}
      />
    </Card>
  );

  if (apsi.compatible) {
    return (
      <section className="reveal space-y-6" data-testid="result" data-result={review_required ? "review" : "compatible"}>
        <Card className="space-y-4">
          <div className="flex justify-center">
            <OverlapCircles phase="compatible" label={review_required ? t("review") : t("compatible")} />
          </div>
          {review_required ? (
            <>
              <StatusChip status="review" size="lg">
                {t("review")}
              </StatusChip>
              <h2 className="text-xl font-semibold">{t("reviewHeadline")}</h2>
              <p data-testid="review-body">{t("reviewBody")}</p>
            </>
          ) : (
            <>
              <StatusChip status="compatible" size="lg">
                {t("compatible")}
              </StatusChip>
              <p className="text-lg">{t("compatibleBody")}</p>
            </>
          )}
          <p className="text-ink-2">{t("notZero")}</p>
        </Card>
        <Notice testId="judicial" icon={Scale}>
          {t("judicial")}
        </Notice>
        {review_required || escalated ? <CounselorHandoff /> : null}
        {thread}
      </section>
    );
  }

  return (
    <section className="reveal space-y-6" data-testid="result" data-result="shared">
      <Card className="space-y-5">
        <div className="flex justify-center">
          <OverlapCircles phase="shared" label={`${t("shared")}: ${shared.map((r) => r.gene).join(", ")}`} overlapText={shared.map((r) => r.gene).join(" · ")} />
        </div>
        <StatusChip status="escalated" size="lg">
          {t("shared")}
        </StatusChip>
        <p className="text-lg">{t("sharedBody")}</p>
        {shared.map((r) => (
          <div key={r.digest} className="space-y-5 border-t border-line pt-5">
            <p>
              <span className="text-ink-2">{t("sharedGene")}: </span>
              <span className="font-mono text-xl font-semibold" data-testid="shared-gene">
                {r.gene}
              </span>
            </p>
            <LockedNumber record={r} field="offspring_risk_one_in" size="giant" label={t("chanceLabel")} />
            <IconArray oneIn={r.offspring_risk_one_in} caption={t("iconCaption")} />
            {r.relative_to_unrelated_display ? (
              <LockedNumber record={r} field="relative_to_unrelated_display" size="large" />
            ) : (
              <p className="text-sm text-ink-2">{t("relativeMissing")}</p>
            )}
            <SourceCaption>{t("source", { version: r.contract_version })}</SourceCaption>
          </div>
        ))}
        <p className="font-semibold">{t("carrierNotDx")}</p>
      </Card>
      <Notice testId="judicial" icon={Scale}>
        {t("judicial")}
      </Notice>
      <CounselorHandoff />
      <OptionCards />
      {thread}
    </section>
  );
}
