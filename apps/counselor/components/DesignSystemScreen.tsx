"use client";
// Living style guide for the counselor workbench (docs/09 §2): every workbench component in its states, Ledger theme,
// EN/AR via the route. Doubles as the Playwright visual-regression target. Sample data = SIMULATED fixtures.
import { Card, CardHeader, PageHeader, SimulatedBadge, type RiskOutput } from "@evolve/ui";
import { PedigreeGraph } from "@evolve/ui";
import { useTranslations } from "next-intl";
import fixtures from "@/lib/mock/fixtures.json";
import type { CaseView, Trigger } from "@/lib/types";
import { TRIGGERS, isOutside } from "@/lib/types";
import { useRelationshipLabel } from "./case/Brief";
import { usePedigreeLabels } from "./case/PedigreeTab";
import { VariantRecord } from "./case/Variants";
import { AccessBasis, OutsideConsent, PriorityChip, SlaTimer, TriggerChip } from "./Workbench";

const views = (fixtures.cases as unknown as { view: CaseView }[]).map((c) => c.view);
const byCouple = (id: string) => views.find((v) => v.case.couple_id === id)!;

export function DesignSystemScreen() {
  const t = useTranslations("ds");
  const tp = useTranslations("pedigree");
  const tc = useTranslations("chrome");
  const rel = useRelationshipLabel();
  const labels = usePedigreeLabels();
  const due = byCouple("V1").case.sla_due_at;
  const dueMs = Date.parse(due);
  const v3 = byCouple("V3").variants.find((v): v is RiskOutput => !isOutside(v))!;
  return (
    <div className="space-y-8" data-testid="design-system">
      <PageHeader title={t("title")} description={t("description")} badge={<SimulatedBadge label={tc("simulated")} />} />

      <Card>
        <CardHeader title={t("chips")} />
        <div className="flex flex-wrap gap-2">
          {TRIGGERS.map((tr: Trigger) => (
            <TriggerChip key={tr} trigger={tr} />
          ))}
          <PriorityChip priority="urgent" />
          <PriorityChip priority="high" />
          <PriorityChip priority="normal" />
        </div>
      </Card>

      <Card>
        <CardHeader title={t("sla")} />
        <div className="flex flex-wrap gap-6">
          <SlaTimer due={due} fixedNow={dueMs - 46 * 3_600_000} />
          <SlaTimer due={due} fixedNow={dueMs - 5 * 3_600_000} />
          <SlaTimer due={due} fixedNow={dueMs + 3 * 3_600_000} />
          <SlaTimer due={due} status="closed" />
        </div>
      </Card>

      <Card>
        <CardHeader title={t("access")} />
        <div className="flex flex-wrap gap-3">
          <AccessBasis coupleConsent onShift />
          <AccessBasis coupleConsent={false} onShift />
          <AccessBasis onShift={false} />
        </div>
      </Card>

      <Card>
        <CardHeader title={t("outside")} />
        <OutsideConsent />
        <div className="mt-4">
          <VariantRecord r={v3} />
        </div>
      </Card>

      {(["V1", "V5", "V2"] as const).map((id) => {
        const p = byCouple(id).pedigree!;
        return (
          <Card key={id}>
            <CardHeader title={`${t("pedigree")} · ${rel(p.relationship)}`} />
            <PedigreeGraph nodes={p.nodes} edges={p.edges} labels={labels} title={tp("title", { relationship: rel(p.relationship) })} testId={`ds-pedigree-${id}`} />
          </Card>
        );
      })}
    </div>
  );
}
