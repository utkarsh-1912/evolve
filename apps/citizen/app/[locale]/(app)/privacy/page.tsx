"use client";
// Privacy & sharing (docs/09 §4.1-8): consents (status, scope, expiry, withdraw with ConfirmDialog), own access
// history ("who saw what, when": own AuditEvents, no genes, no counterpart identity), download my data (SIMULATED).
import { AuditTable, ConsentTable, type ConsentRow } from "@evolve/ui/patterns/data-table";
import { Card, CardHeader } from "@evolve/ui/primitives/display";
import { ErrorState, SimulatedBadge } from "@evolve/ui/primitives/feedback";
import { useToast } from "@evolve/ui/primitives/toast";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { Download } from "lucide-react";
import { useTranslations } from "next-intl";
import { useActivity, useConsents, useRevokeConsent, useVault } from "@/lib/queries";
import { useSession } from "@/lib/session";
import { IconAction } from "@evolve/ui/shell/hints";
import { RequireSession, useActivityLine, useFormat } from "@/components/app-helpers";

export default function PrivacyPage() {
  const t = useTranslations("privacy");
  return (
    <RequireSession title={t("signInTitle")} body={t("signInBody")}>
      <PrivacyInner />
    </RequireSession>
  );
}

function PrivacyInner() {
  const t = useTranslations("privacy");
  const tc = useTranslations("chrome");
  const tcompat = useTranslations("compat");
  const f = useFormat();
  const line = useActivityLine();
  const toast = useToast();
  const { session } = useSession();
  const consents = useConsents();
  const activity = useActivity(100);
  const vault = useVault();
  const revoke = useRevokeConsent();
  const me = session?.partner_id ?? "";

  const rows: ConsentRow[] = (consents.data ?? []).map((c) => ({
    id: c.id,
    status: c.status,
    direction: c.patient === me ? "given" : "received",
    scopeLabel: t("scope"),
    expires_at: c.period.end,
  }));

  function download() {
    // SIMULATED export: only the caller's own data already in this session (no counterpart data).
    const blob = new Blob(
      [JSON.stringify({ simulated: true, partner_id: me, results: vault.data ?? null, consents: rows, activity: activity.data ?? [] }, null, 2)],
      { type: "application/json" },
    );
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `evolve-${me}-data-simulated.json`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast({ title: t("downloaded"), tone: "success" });
  }

  return (
    <>
      <PageHeader
        title={t("title")}
        description={t("description")}
        badge={<SimulatedBadge label={tc("simulated")} />}
        actions={
<IconAction label={t("download")} icon={Download} variant="secondary" onClick={download} data-testid="download-data" />
        }
      />
      <div className="space-y-8">
        <Card>
          <CardHeader title={t("consents")} />
          {consents.isError ? (
            <ErrorState onRetry={() => consents.refetch()} reference="CONSENTS-LOAD" />
          ) : (
            <ConsentTable
              caption={t("consents")}
              rows={rows}
              loading={consents.isLoading}
              headers={{ scope: t("headers.scope"), direction: t("headers.direction"), status: t("headers.status"), expires: t("headers.expires"), actions: t("headers.actions") }}
              statusLabel={(s) => t(`status.${s}`)}
              directionLabel={(d) => t(`direction.${d}`)}
              formatTs={f.dateTime}
              revoke={{
                label: tcompat("revoke"),
                title: tcompat("revokeTitle"),
                description: tcompat("revokeDescription"),
                consequences: tcompat.raw("revokeConsequences") as string[],
                confirmLabel: tcompat("revokeConfirm"),
                onRevoke: async (id) => {
                  await revoke.mutateAsync(id);
                  toast({ title: tcompat("revoked"), tone: "info" });
                },
              }}
            />
          )}
          {!consents.isLoading && rows.length === 0 ? <p className="mt-3 text-sm text-ink-2">{t("consentsEmpty")}</p> : null}
        </Card>
        <Card>
          <CardHeader title={t("audit")} description={t("auditHelp")} />
          {activity.isError ? (
            <ErrorState onRetry={() => activity.refetch()} reference="ACTIVITY-LOAD" />
          ) : (
            <AuditTable
              caption={t("audit")}
              rows={activity.data ?? []}
              loading={activity.isLoading}
              headers={{ when: t("headers.when"), who: t("headers.who"), what: t("headers.what") }}
              formatTs={f.dateTime}
              describe={line}
            />
          )}
        </Card>
      </div>
    </>
  );
}
