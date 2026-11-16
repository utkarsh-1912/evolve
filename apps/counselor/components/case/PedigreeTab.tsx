"use client";
// Pedigree tab: GA4GH pedigree as SVG with consanguinity loops; F shown as genome-wide context only, through
// LockedNumber bound to a consented locked record that carries F (P-01, P-03).
import { LockedNumber, PermissionState, type RiskOutput } from "@evolve/ui";
import { PedigreeGraph, type PedigreeLabels } from "@evolve/ui";
import { useMessages, useTranslations } from "next-intl";
import type { CaseView } from "@/lib/types";
import { isOutside } from "@/lib/types";
import { useRelationshipLabel } from "./Brief";

export function usePedigreeLabels(): Partial<PedigreeLabels> {
  const m = useMessages() as unknown as { pedigree: { labels: Partial<PedigreeLabels> } };
  return m.pedigree.labels;
}

export function PedigreeTab({ view }: { view: CaseView }) {
  const t = useTranslations("pedigree");
  const tc = useTranslations("case");
  const rel = useRelationshipLabel();
  const labels = usePedigreeLabels();
  const ped = view.pedigree;
  if (!view.access_basis.couple_consent || !ped) return <PermissionState body={tc("noConsentBody")} />;
  // F lives in the locked RiskOutput records; pick a consented record that carries it (no arithmetic, P-02).
  const fRecord = view.variants.find((v): v is RiskOutput => !isOutside(v) && v.F !== null && v.F !== undefined);
  return (
    <PedigreeGraph
      nodes={ped.nodes}
      edges={ped.edges}
      title={t("title", { relationship: rel(ped.relationship) })}
      labels={labels}
      context={
        <div className="flex flex-wrap items-start gap-x-8 gap-y-3 rounded-md border border-line p-3">
          <p>
            <span className="block text-ink-2">{tc("tabs.pedigree")}</span>
            <span className="font-semibold">{rel(ped.relationship)}</span>
          </p>
          <div>
            {fRecord ? (
              <LockedNumber record={fRecord} field="F" label={t("fLabel")} />
            ) : (
              <p className="text-ink-2">
                {t("fLabel")}: {t("fMissing")}
              </p>
            )}
          </div>
          <p className="max-w-[60ch] text-ink-2">{t("fNote")}</p>
        </div>
      }
    />
  );
}
