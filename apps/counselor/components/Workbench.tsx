"use client";
// Small workbench building blocks: TriggerChip, PriorityChip, SlaTimer, AccessBasis, LoopStateLabel, OutsideConsent.
import { StatusChip, useUI, type Status } from "@evolve/ui";
import { AlarmClock, Check, Lock, ShieldCheck, X } from "lucide-react";
import { useTranslations } from "next-intl";
import type { CaseStatus, CoupleStatus, Priority, Trigger } from "@/lib/types";
import { LOOP_STATES } from "@/lib/types";
import { useNow } from "./format";

const TRIGGER_TONE: Record<Trigger, Status> = { a: "escalated", b: "review", c: "review", d: "info", gate: "escalated" };

export function TriggerChip({ trigger, size = "sm" }: { trigger: Trigger; size?: "sm" | "md" }) {
  const t = useTranslations("triggers");
  return (
    <StatusChip status={TRIGGER_TONE[trigger]} size={size}>
      <span className="font-mono">{trigger === "gate" ? "gate" : `(${trigger})`}</span> {t(trigger)}
    </StatusChip>
  );
}

const PRIORITY_TONE: Record<Priority, Status> = { urgent: "escalated", high: "review", normal: "neutral" };

export function PriorityChip({ priority }: { priority: Priority }) {
  const t = useTranslations("priority");
  return (
    <StatusChip status={PRIORITY_TONE[priority]} size="sm">
      {t(priority)}
    </StatusChip>
  );
}

/** SLA countdown against the 48 h target (sla_due_at from the backend). Time arithmetic only, never risk. */
export function SlaTimer({ due, status, fixedNow }: { due: string; status?: CaseStatus; fixedNow?: number }) {
  const t = useTranslations("sla");
  const live = useNow();
  const now = fixedNow ?? live;
  if (status === "closed") {
    return (
      <StatusChip status="neutral" size="sm">
        {t("closed")}
      </StatusChip>
    );
  }
  if (now === null) return <span className="text-sm text-ink-2">…</span>;
  const diff = Date.parse(due) - now;
  const abs = Math.abs(diff);
  const h = Math.floor(abs / 3_600_000);
  const m = Math.floor((abs % 3_600_000) / 60_000);
  const overdue = diff < 0;
  const tone: Status = overdue ? "escalated" : h < 12 ? "review" : "neutral";
  return (
    <span className="inline-flex flex-col gap-0.5" data-testid="sla-timer" data-overdue={overdue || undefined}>
      <StatusChip status={tone} size="sm" icon={AlarmClock}>
        <time dateTime={due}>{overdue ? t("overdue", { h, m }) : t("left", { h, m })}</time>
      </StatusChip>
      <span className="text-xs text-ink-2">{t("target")}</span>
    </span>
  );
}

/** "Viewing under: couple consent ✔ · on shift ✔" (docs/09 §4.2 (4)); shown on every case screen. */
export function AccessBasis({ coupleConsent, onShift }: { coupleConsent?: boolean; onShift: boolean }) {
  const t = useTranslations("access");
  const item = (ok: boolean, label: string) => (
    <span className="inline-flex items-center gap-1.5">
      {label}
      {ok ? <Check aria-hidden className="size-4 text-compatible-ink" strokeWidth={3} /> : <X aria-hidden className="size-4 text-escalated-ink" strokeWidth={3} />}
      <span className="sr-only">({ok ? t("granted") : t("missing")})</span>
    </span>
  );
  return (
    <p className="inline-flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md border border-line bg-surface-2 px-3 py-1.5 text-sm text-ink" data-testid="access-basis">
      <ShieldCheck aria-hidden className="size-4 text-ink-2" />
      <span className="text-ink-2">{t("viewingUnder")}:</span>
      {coupleConsent === undefined ? null : (
        <>
          {item(coupleConsent, t("coupleConsent"))}
          <span aria-hidden>·</span>
        </>
      )}
      {item(onShift, t("onShift"))}
    </p>
  );
}

export function useCoupleStatusLabel() {
  const { labels } = useUI();
  const t = useTranslations("coupleStatus");
  return (s: CoupleStatus) => ((LOOP_STATES as readonly string[]).includes(s) ? labels.loopStates[s as (typeof LOOP_STATES)[number]] : t(s as "no_active_loop"));
}

/** Placeholder for a record outside the consented scope: says nothing about it (docs/09 §4.2). */
export function OutsideConsent() {
  const t = useTranslations("variants");
  return (
    <div className="flex min-h-14 items-center gap-2 rounded-lg border border-dashed border-line-strong px-4 py-3 text-sm text-ink-2" data-testid="outside-consent">
      <Lock aria-hidden className="size-4" />
      {t("outside")}
    </div>
  );
}
