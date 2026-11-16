"use client";
// Variants in consented scope (docs/09 §4.2): counselor sees couple records, counselor_only records and the case
// subjects' own records (backend Workbench.scoped_variants). Anything else arrives as {outside_consent:true} and
// renders as a placeholder that says nothing. Every figure is a LockedNumber bound to its RiskOutput (P-01).
import { Card, LockedNumber, PermissionState, StatusChip, type RiskOutput } from "@evolve/ui";
import { useTranslations } from "next-intl";
import type { CaseView } from "@/lib/types";
import { isOutside } from "@/lib/types";
import { OutsideConsent } from "../Workbench";

export function VariantRecord({ r }: { r: RiskOutput }) {
  const t = useTranslations("variants");
  const fields: { key: "offspring_risk_one_in" | "posterior_carrier_b_one_in" | "reference_unrelated_one_in" | "relative_to_unrelated_display" | "detection_rate"; label: string; format?: "percent" }[] = [
    { key: "offspring_risk_one_in", label: t("offspring") },
    { key: "posterior_carrier_b_one_in", label: t("posterior") },
    { key: "reference_unrelated_one_in", label: t("reference") },
    { key: "relative_to_unrelated_display", label: t("relative") },
    { key: "detection_rate", label: t("detection"), format: "percent" },
  ];
  // Show only fields the locked record carries (null = "not calculated" is shown for the primary figure).
  const shown = fields.filter((f) => f.key === "offspring_risk_one_in" || (r[f.key] !== null && r[f.key] !== undefined));
  return (
    <Card as="article" variant="flat" className="space-y-4" data-testid="variant-record" data-gene={r.gene}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-lg font-semibold text-ink">
          <span className="sr-only">{t("gene")}: </span>
          <span className="font-mono" dir="ltr">
            {r.gene}
          </span>{" "}
          <span className="font-mono text-sm font-normal text-ink-2" dir="ltr">
            HGNC:{r.hgnc_id}
          </span>
        </h3>
        <div className="flex flex-wrap gap-2">
          <StatusChip status={r.status === "ok" ? "info" : "review"} size="sm">
            {t(`statuses.${r.status}`)}
          </StatusChip>
          <StatusChip status={r.escalate ? "escalated" : "neutral"} size="sm">
            {r.escalate ? t("escalateYes") : t("escalateNo")}
          </StatusChip>
        </div>
      </div>
      <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
        <dt className="text-ink-2">{t("scenario")}</dt>
        <dd>{t(`scenarios.${r.scenario}`)}</dd>
        <dt className="text-ink-2">{t("audienceLabel")}</dt>
        <dd>{t(`audiences.${r.audience}`)}</dd>
        <dt className="text-ink-2">{t("carrierRole")}</dt>
        <dd>{r.carrier_role ? t(`roles.${r.carrier_role}`) : t("roles.none")}</dd>
        <dt className="text-ink-2">{t("reasonLabel")}</dt>
        <dd>{r.reason ? t(`reasons.${r.reason}`) : t("reasons.none")}</dd>
      </dl>
      <div className="grid gap-4 border-t border-line pt-4 md:grid-cols-2">
        {shown.map((f) => (
          <div key={f.key}>
            <LockedNumber record={r} field={f.key} format={f.format ?? "raw"} label={f.label} size={f.key === "offspring_risk_one_in" ? "large" : "inline"} />
          </div>
        ))}
      </div>
      <p className="break-all text-xs text-ink-2">
        {t("digest")}:{" "}
        <span className="font-mono" dir="ltr">
          {r.digest}
        </span>
      </p>
    </Card>
  );
}

export function VariantsTab({ view }: { view: CaseView }) {
  const t = useTranslations("variants");
  const tc = useTranslations("case");
  if (!view.access_basis.couple_consent) return <PermissionState body={tc("noConsentBody")} />;
  return (
    <section className="space-y-4" aria-labelledby="variants-h">
      <div className="space-y-1">
        <h2 id="variants-h" className="text-lg font-semibold text-ink">
          {t("title")}
        </h2>
        <p className="max-w-[72ch] text-sm text-ink-2">{t("description")}</p>
      </div>
      {view.variants.length === 0 ? (
        <p className="text-sm text-ink-2">{t("empty")}</p>
      ) : (
        <ul className="space-y-3" data-testid="variants-list">
          {view.variants.map((v, i) => (
            <li key={isOutside(v) ? `outside-${i}` : v.digest}>{isOutside(v) ? <OutsideConsent /> : <VariantRecord r={v} />}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
