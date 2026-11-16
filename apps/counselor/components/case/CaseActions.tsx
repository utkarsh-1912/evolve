"use client";
// Case actions (docs/09 §4.2 (3)): advance loop, SURE outcome, schedule (SIMULATED), document human closure
// (counselor-only, ConfirmDialog with consequences). Disabled for closed cases.
import { Button, ConfirmDialog, Dialog, FormField, Select, Textarea, useToast, useUI } from "@evolve/ui";
import { CalendarPlus, ClipboardCheck, FastForward, Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useAdvanceLoop, useClosure, useCreateTask } from "@/lib/queries";
import type { CaseView, LoopState } from "@/lib/types";
import { LOOP_STATES } from "@/lib/types";

export function CaseActions({ view }: { view: CaseView }) {
  const t = useTranslations("actions");
  const tb = useTranslations("brief");
  const { labels } = useUI();
  const toast = useToast();
  const advance = useAdvanceLoop();
  const closure = useClosure();
  const createTask = useCreateTask();
  const c = view.case;
  const closed = c.status === "closed";

  const [advOpen, setAdvOpen] = useState(false);
  const [to, setTo] = useState<LoopState | "">("");
  const [sureOpen, setSureOpen] = useState(false);
  const [closeOpen, setCloseOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [summary, setSummary] = useState("");
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const current = (LOOP_STATES as readonly string[]).includes(c.couple_status) ? (c.couple_status as LoopState) : null;
  const curIdx = current ? LOOP_STATES.indexOf(current) : -1;
  const forward = current ? LOOP_STATES.filter((s, i) => i > curIdx && s !== "HumanClosure") : [];
  const skipped = to ? LOOP_STATES.filter((s, i) => i > curIdx && i < LOOP_STATES.indexOf(to)) : [];

  if (closed) {
    return (
      <p className="inline-flex items-center gap-2 text-sm text-ink-2" data-testid="closed-notice">
        <Lock aria-hidden className="size-4" />
        {t("closedNotice")}
      </p>
    );
  }

  return (
    <div role="group" aria-label={t("label")} className="flex flex-wrap items-center gap-2" data-testid="case-actions">
      {/* Advance loop */}
      <Dialog
        open={advOpen}
        onOpenChange={(o) => {
          setAdvOpen(o);
          if (!o) setTo("");
        }}
        title={t("advanceTitle")}
        description={t("advanceHelp")}
        trigger={
          <Button size="sm" variant="secondary" leadingIcon={<FastForward aria-hidden />} disabled={!current} data-testid="action-advance">
            {t("advance")}
          </Button>
        }
        footer={
          <Button
            disabled={!to}
            loading={advance.isPending}
            data-testid="advance-confirm"
            onClick={async () => {
              if (!to) return;
              try {
                await advance.mutateAsync({ coupleId: c.couple_id, to });
                toast({ title: t("advanced"), tone: "success" });
                setAdvOpen(false);
                setTo("");
              } catch {
                toast({ title: t("advanceError"), tone: "danger" });
              }
            }}
          >
            {t("advanceConfirm")}
          </Button>
        }
      >
        {forward.length ? (
          <>
            <FormField label={t("advanceTo")}>
              <Select value={to} placeholder={t("advancePlaceholder")} onValueChange={(v) => setTo(v as LoopState)} options={forward.map((s) => ({ value: s, label: labels.loopStates[s] }))} />
            </FormField>
            {skipped.length ? <p className="text-sm text-ink-2">{t("advanceSkips", { states: skipped.map((s) => labels.loopStates[s]).join(", ") })}</p> : null}
          </>
        ) : (
          <p className="text-sm text-ink-2">{t("noForward")}</p>
        )}
      </Dialog>

      {/* SURE outcome: answered by each partner in their app; the counselor sees the recorded result and can send a check. */}
      <Dialog
        open={sureOpen}
        onOpenChange={setSureOpen}
        title={t("sureTitle")}
        description={t("sureBody")}
        trigger={
          <Button size="sm" variant="secondary" leadingIcon={<ClipboardCheck aria-hidden />} data-testid="action-sure">
            {t("sure")}
          </Button>
        }
        footer={
          <Button
            variant="secondary"
            loading={createTask.isPending}
            data-testid="sure-send"
            onClick={async () => {
              try {
                await createTask.mutateAsync({ caseId: c.case_id, kind: "sure_check" });
                toast({ title: t("sureSent"), tone: "success" });
                setSureOpen(false);
              } catch {
                toast({ title: t("advanceError"), tone: "danger" });
              }
            }}
          >
            {t("sureSend")}
          </Button>
        }
      >
        <div>
          <p className="mb-2 text-sm font-semibold">{t("sureRecorded")}</p>
          <ul className="space-y-1 text-sm" data-testid="sure-recorded">
            {Object.entries(view.brief.comprehension).map(([pid, x]) => (
              <li key={pid}>
                <span className="font-mono" dir="ltr">
                  {pid}
                </span>
                : {x.sure ? tb("sureScore", { score: x.sure.score }) : tb("notTaken")}
              </li>
            ))}
          </ul>
        </div>
      </Dialog>

      {/* Schedule (SIMULATED) */}
      <ConfirmDialog
        tone="primary"
        trigger={
          <Button size="sm" variant="secondary" leadingIcon={<CalendarPlus aria-hidden />} data-testid="action-schedule">
            {t("schedule")}
          </Button>
        }
        title={t("scheduleTitle")}
        consequences={[t("scheduleConsequence1"), t("scheduleConsequence2"), t("scheduleConsequence3")]}
        confirmLabel={t("scheduleConfirm")}
        testId="schedule-dialog"
        onConfirm={async () => {
          try {
            await createTask.mutateAsync({ caseId: c.case_id, kind: "appointment" });
            toast({ title: t("scheduled"), tone: "success" });
          } catch {
            toast({ title: t("advanceError"), tone: "danger" });
          }
        }}
      />

      {/* Document human closure: summary first, then an explicit confirmation with consequences. */}
      <Dialog
        open={closeOpen}
        onOpenChange={setCloseOpen}
        title={t("closureTitle")}
        trigger={
          <Button size="sm" variant="lime" data-testid="action-closure">
            {t("closure")}
          </Button>
        }
        footer={
          <Button
            data-testid="closure-next"
            onClick={() => {
              if (!summary.trim()) {
                setSummaryError(t("closureRequired"));
                return;
              }
              setSummaryError(null);
              setCloseOpen(false);
              setConfirmOpen(true);
            }}
          >
            {t("closureNext")}
          </Button>
        }
      >
        <FormField label={t("closureLabel")} help={t("closureHelp")} error={summaryError ?? undefined} required>
          <Textarea value={summary} onChange={(e) => setSummary(e.target.value)} maxLength={5000} rows={5} data-testid="closure-summary" />
        </FormField>
      </Dialog>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("closureConfirmTitle")}
        consequences={[t("closureConsequence1"), t("closureConsequence2"), t("closureConsequence3"), t("closureConsequence4")]}
        confirmLabel={t("closureConfirm")}
        testId="closure-confirm"
        onConfirm={async () => {
          try {
            await closure.mutateAsync({ caseId: c.case_id, summary });
            setSummary("");
            toast({ title: t("closed"), tone: "success" });
          } catch {
            toast({ title: t("closureError"), tone: "danger" });
          }
        }}
      />
    </div>
  );
}
