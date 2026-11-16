"use client";
// Family (docs/09 §4.1-7, R-PRIV-4): single-locus cascade screening token for the caller's OWN P/LP finding,
// shown as QR + code, with an explicit "shared / not shared" explanation. Share sheet is SIMULATED.
import { QRCode } from "@evolve/ui/patterns/qr";
import { Button } from "@evolve/ui/primitives/button";
import { Card, CardHeader } from "@evolve/ui/primitives/display";
import { EmptyState, ErrorState, LoadingRegion, SimulatedBadge, Skeleton } from "@evolve/ui/primitives/feedback";
import { FormField } from "@evolve/ui/primitives/field";
import { Select } from "@evolve/ui/primitives/select";
import { useToast } from "@evolve/ui/primitives/toast";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { Check, Copy, Share2, UsersRound, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { useFamilyToken, useVault } from "@/lib/queries";
import { IconAction } from "@evolve/ui/shell/hints";
import { conditionOf } from "@/lib/display";
import { RequireSession, useFormat } from "@/components/app-helpers";

export default function FamilyPage() {
  const t = useTranslations("family");
  return (
    <RequireSession title={t("signInTitle")} body={t("signInBody")}>
      <FamilyInner />
    </RequireSession>
  );
}

function FamilyInner() {
  const t = useTranslations("family");
  const tc = useTranslations("chrome");
  const locale = useLocale();
  const f = useFormat();
  const toast = useToast();
  const vault = useVault();
  const mint = useFamilyToken();
  const [picked, setPicked] = useState<string | undefined>(undefined);
  const header = <PageHeader title={t("title")} description={t("description")} badge={<SimulatedBadge label={tc("simulated")} />} />;

  if (vault.isLoading)
    return (
      <>
        {header}
        <LoadingRegion>
          <Skeleton className="h-72" rounded="lg" />
        </LoadingRegion>
      </>
    );
  if (vault.isError || !vault.data)
    return (
      <>
        {header}
        <ErrorState onRetry={() => vault.refetch()} reference="FAMILY-LOAD" />
      </>
    );

  const eligible = vault.data.calls.filter((c) => c.classification === "P" || c.classification === "LP");
  const chosen = picked ?? (eligible.length ? String(eligible[0].hgnc_id) : undefined);
  const tok = mint.data;

  return (
    <>
      {header}
      {eligible.length === 0 ? (
        <EmptyState icon={UsersRound} title={t("noneTitle")} body={t("noneBody")} testId="family-none" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          <Card className="space-y-5 lg:col-span-7">
            <FormField label={t("pick")}>
              <Select
                value={chosen}
                onValueChange={(v) => {
                  setPicked(v);
                  mint.reset();
                }}
                options={eligible.map((c) => ({ value: String(c.hgnc_id), label: conditionOf(c, locale) ?? c.gene }))}
              />
            </FormField>
            <Button data-testid="family-create" disabled={!chosen} loading={mint.isPending} onClick={() => chosen && mint.mutate(Number(chosen))}>
              {t("create")}
            </Button>
            {mint.isError ? <ErrorState reference="FAMILY-TOKEN" onRetry={() => chosen && mint.mutate(Number(chosen))} /> : null}
            {tok ? (
              <div className="grid gap-5 border-t border-line pt-5 sm:grid-cols-[auto_1fr]" data-testid="family-token">
                <div className="justify-self-center rounded-lg border border-line bg-white p-2">
                  <QRCode value={tok.qr_payload} label={t("qrLabel")} size={220} />
                </div>
                <div className="min-w-0 space-y-3">
                  <h2 className="text-lg font-semibold">{t("tokenTitle")}</h2>
                  <p className="text-sm text-ink-2">{t("tokenHelp")}</p>
                  <p className="text-sm">{t("expires", { date: f.date(tok.expires_at) })}</p>
                  <p className="break-all rounded-md bg-surface-2 p-2 font-mono text-xs" dir="ltr" data-testid="family-payload">
                    {tok.qr_payload}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <IconAction
                      label={t("copy")}
                      icon={Copy}
                      variant="secondary"
                      onClick={async () => {
                        await navigator.clipboard?.writeText(tok.qr_payload).catch(() => {});
                        toast({ title: t("copied"), tone: "success" });
                      }}
                    />
                    <IconAction label={t("share")} icon={Share2} variant="secondary" onClick={() => toast({ title: t("shareSim"), tone: "info" })} />
                  </div>
                </div>
              </div>
            ) : null}
          </Card>
          <Card className="space-y-5 lg:col-span-5">
            <CardHeader title={t("shared")} level={2} />
            <ul className="space-y-2 text-sm">
              {(t.raw("sharedItems") as string[]).map((x) => (
                <li key={x} className="flex gap-2">
                  <Check aria-hidden className="size-4 shrink-0 text-compatible-ink" />
                  {x}
                </li>
              ))}
            </ul>
            <CardHeader title={t("notShared")} level={2} />
            <ul className="space-y-2 text-sm">
              {(t.raw("notSharedItems") as string[]).map((x) => (
                <li key={x} className="flex gap-2">
                  <X aria-hidden className="size-4 shrink-0 text-ink-2" />
                  {x}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </>
  );
}
