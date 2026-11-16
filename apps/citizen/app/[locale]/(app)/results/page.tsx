"use client";
// My results (docs/09 §4.1-2): FindingCards grouped "Needs a conversation" / "For your information", each with a
// detail drawer (plain explanation, technical details, confirmatory recommendation, "Who can see this").
// Own calls only (P-06). Condition name first (A3); Arabic condition when the backend provides condition_ar.
import { FindingCard } from "@evolve/ui/patterns/patterns";
import { Button } from "@evolve/ui/primitives/button";
import { VisibilityChip } from "@evolve/ui/primitives/display";
import { EmptyState, ErrorState, LoadingRegion, SimulatedBadge, Skeleton } from "@evolve/ui/primitives/feedback";
import { Drawer } from "@evolve/ui/primitives/dialog";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { ArrowRight, ClipboardCheck, PanelRightOpen } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Link } from "@/i18n/navigation";
import { useVault } from "@/lib/queries";
import { IconAction } from "@evolve/ui/shell/hints";
import type { RiskOutput, VaultCall } from "@/lib/types";
import { conditionOf } from "@/lib/display";
import { RequireSession } from "@/components/app-helpers";

export default function ResultsPage() {
  const t = useTranslations("results");
  return (
    <RequireSession title={t("signInTitle")} body={t("signInBody")}>
      <ResultsInner />
    </RequireSession>
  );
}

function ResultsInner() {
  const t = useTranslations("results");
  const tc = useTranslations("chrome");
  const tui = useTranslations("ui");
  const locale = useLocale();
  const vault = useVault();
  const [open, setOpen] = useState<number | null>(null);
  const header = <PageHeader title={t("title")} description={t("description")} badge={<SimulatedBadge label={tc("simulated")} />} />;

  if (vault.isLoading)
    return (
      <>
        {header}
        <LoadingRegion>
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-56" rounded="lg" />
            <Skeleton className="h-56" rounded="lg" />
          </div>
        </LoadingRegion>
      </>
    );
  if (vault.isError || !vault.data)
    return (
      <>
        {header}
        <ErrorState onRetry={() => vault.refetch()} reference="RESULTS-LOAD" />
      </>
    );

  const { calls, records } = vault.data;
  const recFor = (c: VaultCall): RiskOutput[] => records.filter((r) => r.hgnc_id === c.hgnc_id);
  const needsConversation = (c: VaultCall) =>
    c.confirmatory_recommended || c.classification === "VUS" || recFor(c).some((r) => r.escalate || r.status === "needs_counselor" || r.audience === "couple");
  const explainable = (c: VaultCall) => recFor(c).some((r) => r.audience === "carrier_partner_only" && r.status === "ok" && r.scenario === "discordant");
  const groups = [
    { key: "conversation" as const, title: t("conversation"), help: t("conversationHelp"), items: calls.filter(needsConversation) },
    { key: "info" as const, title: t("info"), help: undefined, items: calls.filter((c) => !needsConversation(c)) },
  ].filter((g) => g.items.length);
  const current = calls.find((c) => c.hgnc_id === open) ?? null;

  return (
    <>
      {header}
      {calls.length === 0 ? (
        <EmptyState icon={ClipboardCheck} title={t("noneTitle")} body={t("noneBody")} testId="vault-none" />
      ) : (
        <div className="space-y-8" data-testid="vault-calls">
          {groups.map((g) => (
            <section key={g.key} aria-labelledby={`grp-${g.key}`} className="space-y-3">
              <div>
                <h2 id={`grp-${g.key}`} className="text-lg font-semibold">
                  {g.title} <span className="font-normal text-ink-2">({g.items.length})</span>
                </h2>
                {g.help ? <p className="text-sm text-ink-2">{g.help}</p> : null}
              </div>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {g.items.map((c) => (
                  <FindingCard
                    key={c.hgnc_id}
                    testId={`finding-${c.hgnc_id}`}
                    condition={conditionOf(c, locale)}
                    fallbackTitle={t("fallbackTitle")}
                    summary={locale === "ar" ? c.plain_ar : c.plain_en}
                    gene={c.gene}
                    classification={c.classification}
                    zygosity={c.zygosity}
                    visibility="only_you"
                    group={g.key}
                    groupLabel={g.title}
                    confirmatory={c.confirmatory_recommended ? t("confirmatory") : undefined}
                    action={<IconAction label={t("details")} icon={PanelRightOpen} variant="secondary" onClick={() => setOpen(c.hgnc_id)} data-testid={`details-${c.hgnc_id}`} />}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      <Drawer open={!!current} onOpenChange={(o) => !o && setOpen(null)} title={current ? (conditionOf(current, locale) ?? t("fallbackTitle")) : ""} testId="finding-drawer">
        {current ? (
          <div className="space-y-5 text-sm">
            <section>
              <h3 className="font-semibold">{t("drawerMeaning")}</h3>
              <p className="mt-1 text-base">{locale === "ar" ? current.plain_ar : current.plain_en}</p>
            </section>
            <section>
              <h3 className="font-semibold">{t("drawerWho")}</h3>
              <div className="mt-2 space-y-2">
                <VisibilityChip visibility="only_you" />
                <p>{t("drawerWhoBody")}</p>
              </div>
            </section>
            {current.confirmatory_recommended ? (
              <section>
                <h3 className="font-semibold">{t("drawerConfirm")}</h3>
                <p className="mt-1">{t("confirmatory")}</p>
              </section>
            ) : null}
            <section className="rounded-md bg-surface-2 p-3">
              <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1">
                <dt className="text-ink-2">{tui("gene")}</dt>
                <dd className="font-mono" dir="ltr">
                  {current.gene}
                </dd>
                <dt className="text-ink-2">HGNC</dt>
                <dd className="font-mono" dir="ltr">
                  {current.hgnc_id}
                </dd>
                <dt className="text-ink-2">{tui("classification")}</dt>
                <dd className="font-mono" dir="ltr">
                  {current.classification}
                  {current.zygosity ? ` · ${current.zygosity}` : ""}
                </dd>
              </dl>
            </section>
            <section>
              <h3 className="font-semibold">{t("drawerNext")}</h3>
              {!explainable(current) ? <p className="mt-1">{records.length === 0 ? t("explainerAvailable") : t("drawerNextBody")}</p> : null}
              {explainable(current) ? (
                <Button asChild className="mt-2">
                  <Link href="/results/explainer" data-testid="drawer-explainer">
                    {t("explainerLink")}
                    <ArrowRight aria-hidden className="size-4 rtl:-scale-x-100" />
                  </Link>
                </Button>
              ) : null}
            </section>
          </div>
        ) : null}
      </Drawer>
    </>
  );
}
