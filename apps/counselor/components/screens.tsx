"use client";
// Queue, Cases, Calendar (SIMULATED) and Reports screens.
import { DataTable, EmptyState, LoadingRegion, PageHeader, SimulatedBadge, Skeleton, StatCard, StatusChip, type DataColumn } from "@evolve/ui";
import { useQueries } from "@tanstack/react-query";
import { CalendarDays, CheckCircle2, FolderOpen, TimerOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { useMemo } from "react";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { useDensity } from "@/lib/prefs";
import { useCases } from "@/lib/queries";
import { useSession } from "@/lib/session";
import type { FhirTask, Trigger } from "@/lib/types";
import { TRIGGERS } from "@/lib/types";
import { CaseSearch } from "./CaseSearch";
import { CaseTable } from "./CaseTable";
import { patientId, useFormatTs, useNow } from "./format";
import { GateForError, ShiftGate } from "./ShiftGate";
import { AccessBasis, TriggerChip } from "./Workbench";

export function QueueScreen({ mode }: { mode: "queue" | "all" }) {
  const t = useTranslations(mode === "queue" ? "queue" : "cases");
  const { session } = useSession();
  return (
    <>
      <PageHeader title={t("title")} description={t("description")} actions={<AccessBasis onShift={!!session?.on_shift} />} />
      <ShiftGate>
        <CaseSearch className="mb-5 lg:hidden" testId="case-search-inline" />
        <CaseTable mode={mode} />
      </ShiftGate>
    </>
  );
}

interface Appt {
  task: FhirTask;
  caseId: string;
}

export function CalendarScreen() {
  const t = useTranslations("calendar");
  const tk = useTranslations("tasks");
  const tc = useTranslations("chrome");
  const { session } = useSession();
  const formatTs = useFormatTs();
  const [density] = useDensity();
  const cases = useCases({});
  const views = useQueries({
    queries: (cases.data ?? []).map((r) => ({
      queryKey: ["case", session?.token, r.case_id],
      queryFn: () => api.caseView(session!.token, r.case_id),
      enabled: !!session?.on_shift,
    })),
  });
  const loading = cases.isLoading || views.some((v) => v.isLoading);
  const appts = useMemo(() => {
    const seen = new Map<string, Appt>();
    views.forEach((v) => v.data?.tasks.filter((x) => x.code.text === "appointment").forEach((task) => seen.has(task.id) || seen.set(task.id, { task, caseId: v.data!.case.case_id })));
    return [...seen.values()].sort((a, b) => a.task.authoredOn.localeCompare(b.task.authoredOn));
  }, [views]);
  const columns: DataColumn<Appt>[] = [
    {
      id: "case",
      header: t("cols.case"),
      cell: (a) => (
        <Link href={`/cases/${encodeURIComponent(a.caseId)}`} className="font-mono underline underline-offset-4" dir="ltr">
          {a.caseId}
        </Link>
      ),
    },
    { id: "for", header: t("cols.for"), mono: true, cell: (a) => <span dir="ltr">{patientId(a.task.for.reference)}</span> },
    { id: "status", header: t("cols.status"), cell: (a) => tk(`statuses.${a.task.status}`) },
    { id: "created", header: t("cols.created"), cell: (a) => <time dateTime={a.task.authoredOn}>{formatTs(a.task.authoredOn)}</time>, sortValue: (a) => a.task.authoredOn },
  ];
  return (
    <>
      <PageHeader title={t("title")} description={t("description")} badge={<SimulatedBadge label={tc("simulated")} />} />
      <ShiftGate>
        {cases.error ? (
          <GateForError error={cases.error} onRetry={() => cases.refetch()} />
        ) : (
          <DataTable
            caption={t("caption")}
            columns={columns}
            data={appts}
            getRowId={(a) => a.task.id}
            loading={loading}
            dense={density === "compact"}
            testId="calendar-table"
            emptyState={<EmptyState icon={CalendarDays} title={t("emptyTitle")} body={t("emptyBody")} />}
          />
        )}
      </ShiftGate>
    </>
  );
}

export function ReportsScreen() {
  const t = useTranslations("reports");
  const tc = useTranslations("chrome");
  const cases = useCases({});
  const now = useNow();
  const rows = cases.data ?? [];
  const open = rows.filter((r) => r.status === "open");
  const overdue = now === null ? null : open.filter((r) => Date.parse(r.sla_due_at) < now).length;
  return (
    <>
      <PageHeader title={t("title")} description={t("description")} badge={<SimulatedBadge label={tc("simulated")} />} />
      <ShiftGate>
        {cases.isLoading ? (
          <LoadingRegion>
            <Skeleton className="h-28 w-full" />
          </LoadingRegion>
        ) : cases.error ? (
          <GateForError error={cases.error} onRetry={() => cases.refetch()} />
        ) : (
          <div className="space-y-6" data-testid="reports">
            <div className="grid gap-4 sm:grid-cols-3">
              <StatCard label={t("open")} value={<span data-testid="count-open">{open.length}</span>} icon={FolderOpen} />
              <StatCard label={t("closed")} value={rows.length - open.length} icon={CheckCircle2} />
              <StatCard label={t("overdue")} value={overdue ?? "…"} icon={TimerOff} />
            </div>
            <section aria-labelledby="by-trigger" className="space-y-3">
              <h2 id="by-trigger" className="text-lg font-semibold text-ink">
                {t("byTrigger")}
              </h2>
              <table className="w-full max-w-xl border-collapse text-sm">
                <caption className="sr-only">{t("caption")}</caption>
                <tbody>
                  {TRIGGERS.map((tr: Trigger) => (
                    <tr key={tr} className="border-t border-line">
                      <th scope="row" className="py-2 text-start font-normal">
                        <TriggerChip trigger={tr} />
                      </th>
                      <td className="py-2 text-end font-mono text-base">{open.filter((r) => r.trigger === tr).length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <StatusChip status="neutral" size="sm">
                {tc("footerEnv")}
              </StatusChip>
            </section>
          </div>
        )}
      </ShiftGate>
    </>
  );
}
