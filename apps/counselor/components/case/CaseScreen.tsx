"use client";
// Case view (docs/09 §4.2 (2)) inside a resizable split view (docs/09 §3): case list ↔ detail.
// Header: case ID, trigger, SLA, access basis; tabs: Brief, Pedigree, Variants, Tasks, Notes, Timeline.
import {
  Button,
  EmptyState,
  LoadingRegion,
  PageHeader,
  SimulatedBadge,
  Skeleton,
  StatusChip,
  Tabs,
  cn,
} from "@evolve/ui";
import { ArrowLeft, SearchX } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { Link } from "@/i18n/navigation";
import { useCaseView, useCases } from "@/lib/queries";
import { useSession } from "@/lib/session";
import { ApiError } from "@/lib/types";
import { GateForError, ShiftGate } from "../ShiftGate";
import { AccessBasis, PriorityChip, SlaTimer, TriggerChip } from "../Workbench";
import { AiDraftPanel } from "./AiDraftPanel";
import { BriefTab } from "./Brief";
import { CaseActions } from "./CaseActions";
import { NotesTab } from "./NotesTab";
import { PedigreeTab } from "./PedigreeTab";
import { TasksTab } from "./TasksTab";
import { TimelineTab } from "./TimelineTab";
import { VariantsTab } from "./Variants";

const MIN = 220;
const MAX = 520;

function CaseList({ current }: { current: string }) {
  const t = useTranslations("case");
  const cases = useCases({ status: "open" });
  return (
    <nav aria-label={t("listLabel")} className="h-full overflow-y-auto" data-testid="case-list">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-ink-2">{t("listLabel")}</h2>
      {cases.isLoading ? (
        <LoadingRegion>
          <Skeleton className="h-14 w-full" />
          <Skeleton className="mt-2 h-14 w-full" />
        </LoadingRegion>
      ) : (
        <ul className="space-y-1">
          {(cases.data ?? []).map((r) => (
            <li key={r.case_id}>
              <Link
                href={`/cases/${encodeURIComponent(r.case_id)}`}
                aria-current={r.case_id === current ? "page" : undefined}
                className={cn(
                  "flex min-h-11 flex-col gap-1 rounded-md px-3 py-2 hover:bg-surface-2",
                  r.case_id === current && "bg-surface-2 outline outline-1 outline-line-strong",
                )}
              >
                <span className="font-mono text-sm font-semibold" dir="ltr">
                  {r.case_id}
                </span>
                <span className="flex flex-wrap gap-1">
                  <TriggerChip trigger={r.trigger} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </nav>
  );
}

function Resizer({ width, setWidth, label }: { width: number; setWidth: (w: number) => void; label: string }) {
  const start = useRef<{ x: number; w: number } | null>(null);
  const rtl = typeof document !== "undefined" && document.documentElement.dir === "rtl";
  const clamp = (w: number) => Math.max(MIN, Math.min(MAX, w));
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuemin={MIN}
      aria-valuemax={MAX}
      aria-valuenow={width}
      tabIndex={0}
      data-testid="split-resizer"
      onPointerDown={(e) => {
        start.current = { x: e.clientX, w: width };
        e.currentTarget.setPointerCapture(e.pointerId);
      }}
      onPointerMove={(e) => {
        if (!start.current) return;
        const dx = (e.clientX - start.current.x) * (rtl ? -1 : 1);
        setWidth(clamp(start.current.w + dx));
      }}
      onPointerUp={(e) => {
        start.current = null;
        e.currentTarget.releasePointerCapture(e.pointerId);
      }}
      onKeyDown={(e) => {
        const step = e.shiftKey ? 48 : 16;
        const grow = rtl ? "ArrowLeft" : "ArrowRight";
        const shrink = rtl ? "ArrowRight" : "ArrowLeft";
        if (e.key === grow) setWidth(clamp(width + step));
        else if (e.key === shrink) setWidth(clamp(width - step));
        else if (e.key === "Home") setWidth(MIN);
        else if (e.key === "End") setWidth(MAX);
        else return;
        e.preventDefault();
      }}
      className="group relative hidden w-3 shrink-0 cursor-col-resize items-stretch justify-center lg:flex"
    >
      <span aria-hidden className="w-px bg-line-strong group-hover:w-1 group-hover:bg-lime group-focus-visible:w-1 group-focus-visible:bg-lime" />
    </div>
  );
}

function CaseDetail({ caseId }: { caseId: string }) {
  const t = useTranslations("case");
  const tc = useTranslations("chrome");
  const ts = useTranslations("status");
  const { session } = useSession();
  const q = useCaseView(caseId);
  const [tab, setTab] = useState("brief");
  const [noteText, setNoteText] = useState("");

  if (q.isLoading) {
    return (
      <LoadingRegion>
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="mt-3 h-6 w-1/2" />
        <Skeleton className="mt-6 h-11 w-full" />
        <Skeleton className="mt-4 h-72 w-full" />
      </LoadingRegion>
    );
  }
  if (q.error) {
    if (q.error instanceof ApiError && q.error.status === 404) {
      return (
        <EmptyState
          icon={SearchX}
          title={t("notFoundTitle")}
          body={t("notFoundBody")}
          testId="case-not-found"
          action={
            <Button asChild variant="secondary">
              <Link href="/queue">{t("back")}</Link>
            </Button>
          }
        />
      );
    }
    return <GateForError error={q.error} onRetry={() => q.refetch()} />;
  }
  const view = q.data!;
  const c = view.case;
  const closed = c.status === "closed";
  return (
    <article data-testid="case-view" data-case={c.case_id} data-trigger={c.trigger}>
      <PageHeader
        title={
          <span className="font-mono" dir="ltr">
            {c.case_id}
          </span>
        }
        badge={<SimulatedBadge label={tc("simulated")} />}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span>{t("couple", { id: c.couple_id })}</span>
            <TriggerChip trigger={c.trigger} />
            <PriorityChip priority={c.priority} />
            <SlaTimer due={c.sla_due_at} status={c.status} />
            {closed ? (
              <StatusChip status="neutral" size="sm">
                <span data-testid="case-closed">{ts("closed")}</span>
              </StatusChip>
            ) : null}
          </span>
        }
      />
      <div className="mb-5 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <AccessBasis coupleConsent={view.access_basis.couple_consent} onShift={view.access_basis.on_shift && !!session?.on_shift} />
        <CaseActions view={view} />
      </div>
      <Tabs
        label={t("tabs.label")}
        value={tab}
        onValueChange={setTab}
        tabs={[
          { value: "brief", label: t("tabs.brief"), content: (
              <BriefTab
                view={view}
                onOpenVariants={() => setTab("variants")}
                aiPanel={
                  <AiDraftPanel
                    caseId={c.case_id}
                    readOnly={closed}
                    onCopyToNotes={(text) => {
                      setNoteText(text);
                      setTab("notes");
                    }}
                  />
                }
              />
            ),
          },
          { value: "pedigree", label: t("tabs.pedigree"), content: <PedigreeTab view={view} /> },
          { value: "variants", label: t("tabs.variants"), content: <VariantsTab view={view} /> },
          { value: "tasks", label: t("tabs.tasks"), count: view.tasks.length, content: <TasksTab view={view} readOnly={closed} /> },
          { value: "notes", label: t("tabs.notes"), count: view.notes.length, content: <NotesTab view={view} readOnly={closed} text={noteText} setText={setNoteText} /> },
          { value: "timeline", label: t("tabs.timeline"), content: <TimelineTab view={view} /> },
        ]}
      />
    </article>
  );
}

export function CaseScreen({ caseId }: { caseId: string }) {
  const t = useTranslations("case");
  const [width, setWidth] = useState(280);
  return (
    <ShiftGate>
      <div className="mb-4 lg:hidden">
        <Button asChild variant="ghost" size="sm">
          <Link href="/queue">
            <ArrowLeft aria-hidden className="rtl:-scale-x-100" />
            {t("back")}
          </Link>
        </Button>
      </div>
      <div className="flex gap-3">
        <aside className="hidden shrink-0 lg:block" style={{ width }}>
          <CaseList current={caseId} />
        </aside>
        <Resizer width={width} setWidth={setWidth} label={t("resize")} />
        <div className="min-w-0 flex-1">
          <CaseDetail key={caseId} caseId={caseId} />
        </div>
      </div>
    </ShiftGate>
  );
}
