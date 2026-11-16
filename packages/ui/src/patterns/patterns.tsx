"use client";
// FindingCard (A3), Timeline + CareTimeline (A4), MessageThread (A5).
import { CheckCircle2, ChevronDown, Circle, CircleDashed, CircleDot, MessageSquare, ShieldCheck, UserRound } from "lucide-react";
import { useId, useState, type ReactNode } from "react";
import type { LoopState, Visibility } from "../contracts";
import { LOOP_STATES } from "../contracts";
import { cn } from "../lib/cn";
import { useUI } from "../provider";
import { Card, StatusChip, VisibilityChip } from "../primitives/display";
import { EmptyState, GuardBanner } from "../primitives/feedback";

/**
 * FindingCard: condition name first, plain-language status, gene/classification behind "Technical details" (A3).
 * `group` decides the chip: "conversation" = review (amber), "info" = neutral. Never a red "positive" label.
 */
export function FindingCard({
  condition,
  fallbackTitle,
  summary,
  gene,
  classification,
  zygosity,
  visibility,
  group,
  groupLabel,
  confirmatory,
  action,
  testId,
}: {
  condition?: string | null;
  fallbackTitle: string;
  summary: ReactNode;
  gene: string;
  classification: string;
  zygosity?: string | null;
  visibility: Visibility;
  group: "conversation" | "info";
  groupLabel: string;
  confirmatory?: ReactNode;
  action?: ReactNode;
  testId?: string;
}) {
  const { labels } = useUI();
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <Card as="article" variant="flat" className="flex flex-col gap-4" data-testid={testId} aria-labelledby={`${id}-t`}>
      <div className="flex flex-wrap items-center gap-2">
        <StatusChip status={group === "conversation" ? "review" : "neutral"} size="sm">
          {groupLabel}
        </StatusChip>
        <VisibilityChip visibility={visibility} />
      </div>
      <div className="space-y-2">
        <h3 id={`${id}-t`} className="text-lg font-semibold leading-snug text-ink">
          {condition || fallbackTitle}
        </h3>
        <p className="max-w-[72ch] text-ink">{summary}</p>
      </div>
      {confirmatory ? <div className="rounded-md bg-surface-2 p-3 text-sm text-ink">{confirmatory}</div> : null}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={`${id}-d`}
          onClick={() => setOpen((o) => !o)}
          className="inline-flex min-h-11 items-center gap-1.5 rounded-md text-sm font-semibold text-ink-2 hover:text-ink"
        >
          {labels.technicalDetails}
          <ChevronDown aria-hidden className={cn("size-4 transition-transform duration-[var(--motion-base)]", open && "rotate-180")} />
        </button>
        {action}
      </div>
      {open ? (
        <dl id={`${id}-d`} className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 rounded-md bg-surface-2 p-3 text-sm" data-testid="technical-details">
          <dt className="text-ink-2">{labels.gene}</dt>
          <dd className="font-mono text-ink" dir="ltr">
            {gene}
          </dd>
          <dt className="text-ink-2">{labels.classification}</dt>
          <dd className="font-mono text-ink" dir="ltr">
            {classification}
          </dd>
          {zygosity ? (
            <>
              <dt className="text-ink-2">{labels.zygosity}</dt>
              <dd className="font-mono text-ink" dir="ltr">
                {zygosity}
              </dd>
            </>
          ) : null}
        </dl>
      ) : null}
    </Card>
  );
}

export interface TimelineItem {
  key: string;
  title: ReactNode;
  /** "skipped": the loop moved past this state without it happening. Never shown as done (P-04, DECISIONS #50). */
  status: "complete" | "current" | "upcoming" | "skipped";
  ts?: string;
  owner?: ReactNode;
  due?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}

/** Timeline: vertical list; the current item is highlighted and announced (aria-current). */
export function Timeline({ items, label, formatTs }: { items: TimelineItem[]; label: string; formatTs?: (iso: string) => string }) {
  const { labels } = useUI();
  return (
    <ol aria-label={label} className="relative space-y-0">
      {items.map((it, i) => {
        const Icon = it.status === "complete" ? CheckCircle2 : it.status === "current" ? CircleDot : it.status === "skipped" ? CircleDashed : Circle;
        return (
          <li key={it.key} aria-current={it.status === "current" ? "step" : undefined} data-status={it.status} className="relative flex gap-4 pb-6 last:pb-0">
            {i < items.length - 1 ? (
              <span aria-hidden className={cn("absolute start-[15px] top-8 h-[calc(100%-2rem)] w-0.5", it.status === "complete" ? "bg-navy" : "bg-line")} />
            ) : null}
            <span
              className={cn(
                "relative z-[1] grid size-8 shrink-0 place-items-center rounded-full",
                it.status === "complete" && "bg-navy text-cream",
                it.status === "current" && "bg-lime text-navy ring-2 ring-navy",
                it.status === "upcoming" && "bg-surface-2 text-ink-2",
                it.status === "skipped" && "border-2 border-dashed border-line-strong bg-surface-1 text-ink-2",
              )}
            >
              <Icon aria-hidden className="size-4" />
            </span>
            <div className={cn("min-w-0 flex-1 pt-1", it.status === "current" && "rounded-lg bg-surface-2 p-3 pt-2")}>
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <p className={cn("font-semibold", it.status === "upcoming" || it.status === "skipped" ? "text-ink-2" : "text-ink", it.status === "skipped" && "line-through decoration-1")}>
                  {it.title}
                  {it.status === "skipped" ? (
                    <span className="ms-2 inline-flex rounded-sm border border-dashed border-line-strong px-1.5 text-xs font-semibold no-underline text-ink-2" data-testid="timeline-skipped">
                      {labels.skipped}
                    </span>
                  ) : (
                    <span className="sr-only">
                      {" "}
                      ({it.status === "complete" ? labels.completed : it.status === "current" ? labels.youAreHere : labels.upcoming})
                    </span>
                  )}
                </p>
                {it.ts ? (
                  <time dateTime={it.ts} className="text-sm text-ink-2">
                    {formatTs ? formatTs(it.ts) : it.ts}
                  </time>
                ) : null}
              </div>
              {it.owner || it.due ? (
                <p className="mt-1 flex flex-wrap gap-x-4 text-sm text-ink-2">
                  {it.owner ? (
                    <span className="inline-flex items-center gap-1">
                      <UserRound aria-hidden className="size-3.5" />
                      {labels.owner}: {it.owner}
                    </span>
                  ) : null}
                  {it.due ? (
                    <span>
                      {labels.due}: {it.due}
                    </span>
                  ) : null}
                </p>
              ) : null}
              {it.description ? <p className="mt-1 text-sm text-ink">{it.description}</p> : null}
              {it.action ? <div className="mt-2">{it.action}</div> : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/** CareTimeline: the 7-state closed loop with timestamps, owner and the next action (A4). */
export function CareTimeline({
  state,
  history,
  ownerFor,
  nextActionFor,
  dueFor,
  formatTs,
  label,
}: {
  state: LoopState;
  history: { state: LoopState; ts?: string; at?: string; actor_role?: string; actor?: string }[];
  ownerFor: (s: LoopState) => ReactNode;
  nextActionFor?: (s: LoopState) => ReactNode;
  dueFor?: (s: LoopState) => ReactNode;
  formatTs?: (iso: string) => string;
  label: string;
}) {
  const { labels } = useUI();
  const idx = LOOP_STATES.indexOf(state);
  const items: TimelineItem[] = LOOP_STATES.map((s, i) => {
    const h = history.find((x) => x.state === s);
    // A past state counts as done only if it is in the history; otherwise the loop jumped over it (P-04).
    const status = i < idx ? (h ? "complete" : "skipped") : i === idx ? "current" : "upcoming";
    return {
      key: s,
      title: labels.loopStates[s],
      status,
      ts: h?.ts ?? h?.at,
      owner: ownerFor(s),
      due: status === "current" && dueFor ? dueFor(s) : undefined,
      action: status === "current" && nextActionFor ? nextActionFor(s) : undefined,
    };
  });
  return (
    <div data-testid="care-timeline">
      <Timeline items={items} label={label} formatTs={formatTs} />
    </div>
  );
}

export interface ThreadMessage {
  id: string;
  kind: "result" | "explainer" | "care" | "escalation";
  text: string;
  ts?: string;
  gatePassed: boolean;
  author: string;
}

/**
 * MessageThread (A5): never an empty container. Empty → EmptyState; gate-held → GuardBanner (text never shown).
 */
export function MessageThread({ messages, title, formatTs, emptyAction }: { messages: ThreadMessage[]; title: string; formatTs?: (iso: string) => string; emptyAction?: ReactNode }) {
  const { labels } = useUI();
  if (messages.length === 0) {
    return <EmptyState icon={MessageSquare} title={title} body={labels.messagesEmpty} action={emptyAction} testId="messages-empty" />;
  }
  return (
    <section aria-label={title} className="space-y-3" data-testid="message-thread">
      {messages.map((m) =>
        m.gatePassed ? (
          <article key={m.id} className="rounded-lg border border-line bg-surface-1 p-4">
            <header className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
              <span className="font-semibold text-ink">{m.author}</span>
              {m.ts ? (
                <time dateTime={m.ts} className="text-ink-2">
                  {formatTs ? formatTs(m.ts) : m.ts}
                </time>
              ) : null}
            </header>
            <p className="max-w-[72ch] text-ink">{m.text}</p>
            <p className="mt-2 inline-flex items-center gap-1.5 text-xs text-ink-2">
              <ShieldCheck aria-hidden className="size-3.5 text-compatible-ink" />
              {labels.gatePassed}
            </p>
          </article>
        ) : (
          <GuardBanner key={m.id} />
        ),
      )}
    </section>
  );
}
