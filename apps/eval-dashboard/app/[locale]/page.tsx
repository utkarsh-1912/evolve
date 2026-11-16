import { setRequestLocale } from "next-intl/server";
import { useTranslations } from "next-intl";
import { use } from "react";
import { PageHeader, SimulatedBadge } from "@evolve/ui";
import { CalibrationHistogram, CohortGrid } from "@/components/CohortPanel";
import { EvalShell } from "@/components/EvalShell";
import { Gate3 } from "@/components/Gate3";
import { GatePanel, LeakagePanel, SimVsRealTable, TestMatrix } from "@/components/EvidenceTables";
import { Assumptions } from "@/components/Header";
import { LiveSection } from "@/components/LiveSection";
import { MetricPanels } from "@/components/MetricPanels";
import { Section } from "@/components/bits";

// Eval dashboard (R-EVAL-1 presentation; TASK-P4-UI-EVAL + Gate probe, DECISIONS #38; clean-UI Wave B, DECISIONS #52).
// One SIMULATED badge for the surface (next to the title); simulation is also stated in words in every panel's basis
// line and in the simulated-vs-real table.
export default function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations();
  return (
    <EvalShell>
      <PageHeader title={t("header.title")} description={t("header.lead")} badge={<SimulatedBadge label={t("chrome.simulated")} />} />
      <Section id="simreal" label={t("sections.simreal")} title={t("simreal.title")} description={t("simreal.description")}>
        <SimVsRealTable />
      </Section>
      <Section id="dimensions" label={t("sections.dimensions")} title={t("sections.dimensions")}>
        <MetricPanels />
      </Section>
      <Section id="gate" label={t("sections.gate")} title={t("gate.title")} description={t("gate.description")}>
        <GatePanel />
      </Section>
      <Section id="leakage" label={t("sections.leakage")} title={t("leak.title")}>
        <LeakagePanel />
      </Section>
      <Section id="cohort" label={t("sections.cohort")} title={t("cohort.title")} description={t("cohort.description")}>
        <div className="grid gap-10 xl:grid-cols-2">
          <CohortGrid />
          <div className="space-y-3">
            <h3 className="font-display text-xl font-semibold text-ink">{t("cohort.histTitle")}</h3>
            <p className="max-w-[72ch] text-sm text-ink-2">{t("cohort.histDescription")}</p>
            <CalibrationHistogram />
          </div>
        </div>
      </Section>
      <Section id="tests" label={t("sections.tests")} title={t("tests.title")} description={t("tests.description")}>
        <TestMatrix />
        <Gate3 />
      </Section>
      <Section id="probe" label={t("sections.probe")} title={t("terminal.title")} description={t("terminal.description")}>
        <LiveSection />
      </Section>
      <Section id="assumptions" label={t("sections.assumptions")} title={t("assumptions.title")} description={t("assumptions.description")}>
        <Assumptions />
      </Section>
    </EvalShell>
  );
}
