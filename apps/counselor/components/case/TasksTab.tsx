"use client";
// Tasks (FHIR Task, SIMULATED tag): list, create, progress, complete, cancel (confirm). Targets are chosen by the
// backend from the consented case subjects; the UI never names a recipient (403 outside_consent otherwise, DECISIONS #16).
import {
  Alert,
  Button,
  ConfirmDialog,
  DataTable,
  EmptyState,
  FormField,
  Select,
  StatusChip,
  useToast,
  type DataColumn,
  type RiskOutput,
  type Status,
} from "@evolve/ui";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { useDensity } from "@/lib/prefs";
import { useCreateTask, useUpdateTask } from "@/lib/queries";
import type { CaseView, FhirTask, TaskKind, TaskStatus } from "@/lib/types";
import { ApiError, TASK_KINDS, isOutside } from "@/lib/types";
import { patientId, useFormatTs } from "../format";

const STATUS_TONE: Record<TaskStatus, Status> = { requested: "review", accepted: "info", "in-progress": "info", completed: "compatible", cancelled: "neutral" };

export function TasksTab({ view, readOnly }: { view: CaseView; readOnly: boolean }) {
  const t = useTranslations("tasks");
  const formatTs = useFormatTs();
  const toast = useToast();
  const [density] = useDensity();
  const create = useCreateTask();
  const update = useUpdateTask();
  const [kind, setKind] = useState<TaskKind | "">("");
  const [focus, setFocus] = useState("none");
  const [error, setError] = useState<string | null>(null);
  const caseId = view.case.case_id;

  const genes = useMemo(() => {
    const seen = new Map<number, string>();
    for (const v of view.variants) if (!isOutside(v)) seen.set((v as RiskOutput).hgnc_id, (v as RiskOutput).gene);
    return [...seen.entries()];
  }, [view.variants]);

  const setStatus = (task: FhirTask, status: TaskStatus) =>
    update.mutateAsync({ caseId, taskId: task.id, status }).then(
      () => toast({ title: t("updated"), tone: "success" }),
      () => toast({ title: t("error"), tone: "danger" }),
    );

  const columns: DataColumn<FhirTask>[] = [
    { id: "kind", header: t("cols.kind"), cell: (r) => (t.has(`kinds.${r.code.text}` as "kinds.follow_up") ? t(`kinds.${r.code.text}` as "kinds.follow_up") : r.code.text), sortValue: (r) => r.code.text },
    { id: "for", header: t("cols.for"), mono: true, cell: (r) => <span dir="ltr">{patientId(r.for.reference)}</span>, sortValue: (r) => r.for.reference },
    {
      id: "status",
      header: t("cols.status"),
      sortValue: (r) => r.status,
      cell: (r) => (
        <StatusChip status={STATUS_TONE[r.status]} size="sm">
          {t(`statuses.${r.status}`)}
        </StatusChip>
      ),
    },
    {
      id: "due",
      header: t("cols.due"),
      hideOnMobile: true,
      sortValue: (r) => r.restriction?.period?.end ?? "",
      cell: (r) => (r.restriction?.period?.end ? <time dateTime={r.restriction.period.end}>{formatTs(r.restriction.period.end)}</time> : "—"),
    },
    { id: "focus", header: t("cols.focus"), hideOnMobile: true, mono: true, cell: (r) => <span dir="ltr">{r.focus?.display ?? "—"}</span> },
    {
      id: "actions",
      header: t("cols.actions"),
      align: "end",
      cell: (r) =>
        readOnly || r.status === "completed" || r.status === "cancelled" ? null : (
          <div className="flex flex-wrap justify-end gap-2">
            {r.status === "requested" || r.status === "accepted" ? (
              <Button size="sm" variant="secondary" onClick={() => setStatus(r, "in-progress")}>
                {t("start")}
              </Button>
            ) : null}
            <Button size="sm" variant="secondary" onClick={() => setStatus(r, "completed")} data-testid="task-complete">
              {t("complete")}
            </Button>
            <ConfirmDialog
              trigger={
                <Button size="sm" variant="ghost">
                  {t("cancel")}
                </Button>
              }
              title={t("cancelTitle")}
              consequences={[t("cancelConsequence1"), t("cancelConsequence2")]}
              cancelLabel={t("keep")}
              confirmLabel={t("cancel")}
              onConfirm={() => setStatus(r, "cancelled")}
            />
          </div>
        ),
    },
  ];

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kind) return;
    setError(null);
    try {
      await create.mutateAsync({ caseId, kind, hgnc_id: focus === "none" ? undefined : Number(focus) });
      toast({ title: t("created"), tone: "success" });
      setKind("");
      setFocus("none");
    } catch (err) {
      setError(err instanceof ApiError && err.code === "outside_consent" ? t("outsideConsent") : t("error"));
    }
  };

  return (
    <section className="space-y-5" aria-labelledby="tasks-h" data-testid="tasks">
      <h2 id="tasks-h" className="text-lg font-semibold text-ink">
        {t("title")}
      </h2>
      <p className="max-w-[72ch] text-sm text-ink-2">{t("description")}</p>

      {readOnly ? null : (
        <form onSubmit={submit} className="grid items-end gap-3 rounded-lg border border-line p-4 sm:grid-cols-[1fr_1fr_auto]" data-testid="task-form">
          <FormField label={t("kind")} required>
            <Select
              value={kind}
              placeholder={t("kindPlaceholder")}
              onValueChange={(v) => setKind(v as TaskKind)}
              options={TASK_KINDS.map((k) => ({ value: k, label: t(`kinds.${k}`) }))}
            />
          </FormField>
          <FormField label={t("focus")}>
            <Select
              value={focus}
              onValueChange={setFocus}
              options={[{ value: "none", label: t("focusNone") }, ...genes.map(([id, gene]) => ({ value: String(id), label: `${gene} (HGNC:${id})` }))]}
            />
          </FormField>
          <Button type="submit" disabled={!kind} loading={create.isPending} data-testid="task-create">
            {t("create")}
          </Button>
          {error ? (
            <Alert tone="danger" className="sm:col-span-3" testId="task-error">
              {error}
            </Alert>
          ) : null}
        </form>
      )}

      <DataTable
        caption={t("caption")}
        columns={columns}
        data={view.tasks}
        getRowId={(r) => r.id}
        dense={density === "compact"}
        testId="task-table"
        emptyState={<EmptyState title={t("emptyTitle")} body={t("emptyBody")} />}
      />
    </section>
  );
}
