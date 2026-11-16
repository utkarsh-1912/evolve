"use client";
// Queue / Cases table (docs/09 §4.2 (1)): TanStack DataTable with trigger chips, SLA countdown vs 48 h, filters,
// built-in + saved views, and keyboard navigation (j / k move, Enter opens).
import {
  Button,
  DataTable,
  Dialog,
  EmptyState,
  FormField,
  IconButton,
  Input,
  Select,
  type DataColumn,
} from "@evolve/ui";
import { Filter, Save, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "@/i18n/navigation";
import { useDensity, useSavedViews, type QueueView } from "@/lib/prefs";
import { useCases } from "@/lib/queries";
import type { CaseRow, Priority, Trigger } from "@/lib/types";
import { TRIGGERS } from "@/lib/types";
import { GateForError } from "./ShiftGate";
import { PriorityChip, SlaTimer, TriggerChip, useCoupleStatusLabel } from "./Workbench";

const PRIORITY_ORDER: Record<Priority, number> = { urgent: 0, high: 1, normal: 2 };

export function CaseTable({ mode }: { mode: "queue" | "all" }) {
  const t = useTranslations("queue");
  const tt = useTranslations("triggers");
  const tp = useTranslations("priority");
  const ts = useTranslations("status");
  const router = useRouter();
  const [density] = useDensity();
  const [saved, setSaved] = useSavedViews();
  const coupleLabel = useCoupleStatusLabel();
  const wrap = useRef<HTMLDivElement>(null);

  const builtIn: QueueView[] = useMemo(
    () =>
      mode === "queue"
        ? [
            { id: "open", name: t("builtIn.open"), trigger: "", status: "open", priority: "", builtIn: true },
            { id: "urgent", name: t("builtIn.urgent"), trigger: "", status: "open", priority: "urgent", builtIn: true },
            { id: "understanding", name: t("builtIn.understanding"), trigger: "d", status: "open", priority: "", builtIn: true },
          ]
        : [
            { id: "all", name: t("builtIn.all"), trigger: "", status: "", priority: "", builtIn: true },
            { id: "closed", name: t("builtIn.closed"), trigger: "", status: "closed", priority: "", builtIn: true },
          ],
    [mode, t],
  );
  const [view, setView] = useState<QueueView>(builtIn[0]);
  const [saveOpen, setSaveOpen] = useState(false);
  const [name, setName] = useState("");

  // Server-side filters per contract (status, trigger); priority is filtered locally.
  const cases = useCases({ status: view.status || undefined, trigger: view.trigger || undefined });
  const rows = useMemo(() => (cases.data ?? []).filter((r) => !view.priority || r.priority === view.priority), [cases.data, view.priority]);

  const columns = useMemo<DataColumn<CaseRow>[]>(
    () => [
      {
        id: "case",
        header: t("cols.case"),
        sortValue: (r) => r.case_id,
        cell: (r) => (
          <span className="flex flex-col">
            <span className="font-mono text-sm font-semibold text-ink" dir="ltr" data-testid="case-id">
              {r.case_id}
            </span>
            <span className="font-mono text-xs text-ink-2" dir="ltr">
              {r.couple_id}
            </span>
          </span>
        ),
      },
      { id: "trigger", header: t("cols.trigger"), sortValue: (r) => r.trigger, cell: (r) => <TriggerChip trigger={r.trigger} /> },
      { id: "priority", header: t("cols.priority"), sortValue: (r) => PRIORITY_ORDER[r.priority], cell: (r) => <PriorityChip priority={r.priority} />, hideOnMobile: true },
      { id: "age", header: t("cols.age"), sortValue: (r) => r.sla_due_at, cell: (r) => <SlaTimer due={r.sla_due_at} status={r.status} /> },
      { id: "couple", header: t("cols.couple"), sortValue: (r) => r.couple_status, cell: (r) => coupleLabel(r.couple_status), hideOnMobile: true },
      {
        id: "assigned",
        header: t("cols.assigned"),
        sortValue: (r) => r.assigned_to ?? "",
        cell: (r) => (r.assigned_to ? <span className="font-mono text-xs">{r.assigned_to}</span> : <span className="text-ink-2">{t("unassigned")}</span>),
        hideOnMobile: true,
      },
      ...(mode === "all"
        ? [{ id: "status", header: t("cols.status"), sortValue: (r: CaseRow) => r.status, cell: (r: CaseRow) => ts(r.status) } satisfies DataColumn<CaseRow>]
        : []),
    ],
    [t, ts, mode, coupleLabel],
  );

  // j / k move focus between rows; Enter (handled by DataTable) opens the case.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "j" && e.key !== "k") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      if (el && (el.closest("input, textarea, select, [contenteditable=true], [role=dialog], [role=alertdialog], [role=listbox], [role=menu]"))) return;
      const trs = Array.from(wrap.current?.querySelectorAll<HTMLTableRowElement>("tbody tr[tabindex]") ?? []);
      if (!trs.length) return;
      e.preventDefault();
      const i = trs.indexOf(document.activeElement as HTMLTableRowElement);
      const next = i < 0 ? 0 : e.key === "j" ? Math.min(i + 1, trs.length - 1) : Math.max(i - 1, 0);
      trs[next].focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const views = [...builtIn, ...saved.filter((v) => (mode === "queue" ? v.status !== "closed" : true))];
  const setFilter = (k: "trigger" | "status" | "priority", v: string) => setView({ ...view, id: "custom", name: "", builtIn: false, [k]: v === "any" ? "" : v });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label={t("views")} data-testid="saved-views">
        {views.map((v) => (
          <span key={v.id} className="inline-flex items-center">
            <Button
              size="sm"
              variant={view.id === v.id ? "primary" : "secondary"}
              aria-pressed={view.id === v.id}
              onClick={() => setView(v)}
              className={v.builtIn ? undefined : "rounded-e-none"}
            >
              {v.name}
            </Button>
            {v.builtIn ? null : (
              <IconButton
                label={t("deleteView", { name: v.name })}
                variant="secondary"
                className="rounded-s-none border-s-0"
                onClick={() => {
                  setSaved(saved.filter((s) => s.id !== v.id));
                  if (view.id === v.id) setView(builtIn[0]);
                }}
              >
                <X aria-hidden />
              </IconButton>
            )}
          </span>
        ))}
        <Dialog
          open={saveOpen}
          onOpenChange={setSaveOpen}
          title={t("saveViewTitle")}
          trigger={
            <Button size="sm" variant="ghost" leadingIcon={<Save aria-hidden />} data-testid="save-view">
              {t("saveView")}
            </Button>
          }
          footer={
            <Button
              disabled={!name.trim()}
              onClick={() => {
                const v: QueueView = { id: `v-${Date.now()}`, name: name.trim(), trigger: view.trigger, status: view.status, priority: view.priority };
                setSaved([...saved, v]);
                setView(v);
                setName("");
                setSaveOpen(false);
              }}
            >
              {t("save")}
            </Button>
          }
        >
          <FormField label={t("viewName")} help={t("viewNameHelp")}>
            <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={40} />
          </FormField>
        </Dialog>
      </div>

      <fieldset className="grid gap-3 rounded-lg border border-line p-4 sm:grid-cols-3" data-testid="filters">
        <legend className="flex items-center gap-1.5 px-1 text-sm font-semibold text-ink">
          <Filter aria-hidden className="size-4" />
          {t("filters")}
        </legend>
        <FormField label={t("trigger")}>
          <Select
            value={view.trigger || "any"}
            onValueChange={(v) => setFilter("trigger", v)}
            options={[{ value: "any", label: tt("any") }, ...TRIGGERS.map((x: Trigger) => ({ value: x, label: `${x === "gate" ? "gate" : `(${x})`} ${tt(x)}` }))]}
          />
        </FormField>
        <FormField label={t("priority")}>
          <Select
            value={view.priority || "any"}
            onValueChange={(v) => setFilter("priority", v)}
            options={[{ value: "any", label: tp("any") }, ...(["urgent", "high", "normal"] as const).map((p) => ({ value: p, label: tp(p) }))]}
          />
        </FormField>
        <FormField label={t("status")}>
          <Select
            value={view.status || "any"}
            onValueChange={(v) => setFilter("status", v)}
            options={[{ value: "any", label: ts("any") }, { value: "open", label: ts("open") }, { value: "closed", label: ts("closed") }]}
          />
        </FormField>
      </fieldset>

      <p className="text-sm text-ink-2" id="queue-keyboard">
        {t("keyboard")}
      </p>

      {cases.error ? (
        <GateForError error={cases.error} onRetry={() => cases.refetch()} />
      ) : (
          <div ref={wrap} aria-describedby="queue-keyboard">
            <DataTable
              caption={t("caption")}
              columns={columns}
              data={rows}
              getRowId={(r) => r.case_id}
              loading={cases.isLoading}
              dense={density === "compact"}
              pageSize={25}
              onRowActivate={(r) => router.push(`/cases/${encodeURIComponent(r.case_id)}`)}
              testId="case-table"
              emptyState={
                <EmptyState
                  title={t("emptyTitle")}
                  body={t("emptyBody")}
                  action={
                    <Button size="sm" variant="secondary" onClick={() => setView(builtIn[0])}>
                      {t("clear")}
                    </Button>
                  }
                />
              }
            />
          </div>
      )}
    </div>
  );
}
