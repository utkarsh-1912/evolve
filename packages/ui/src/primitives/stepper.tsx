"use client";
// Tabs, Stepper, Accordion, Breadcrumbs, Pagination.
import { Check } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../lib/cn";
import { fmt, useUI } from "../provider";

/** Tabs (Radix): roving focus, arrow keys mirror in RTL. */

export type StepState = "complete" | "current" | "upcoming";

/** Stepper: wizard progress (e.g. Invite → Both consent → Private check). */
export function Stepper({ steps, label }: { steps: { label: ReactNode; state: StepState; description?: ReactNode }[]; label: string }) {
  const { labels } = useUI();
  const current = steps.findIndex((s) => s.state === "current");
  return (
    <nav aria-label={label}>
      <p className="sr-only">{fmt(labels.stepOf, { n: current + 1, total: steps.length })}</p>
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-2">
        {steps.map((s, i) => (
          <li key={i} aria-current={s.state === "current" ? "step" : undefined} className="flex items-center gap-2">
            <span
              className={cn(
                "grid size-8 shrink-0 place-items-center rounded-full border-2 text-sm font-semibold",
                s.state === "complete" && "border-navy bg-navy text-cream",
                s.state === "current" && "border-navy bg-surface-1 text-navy",
                s.state === "upcoming" && "border-line-strong bg-surface-1 text-ink-2",
              )}
            >
              {s.state === "complete" ? <Check aria-hidden className="size-4" strokeWidth={3} /> : i + 1}
            </span>
            <span className={cn("text-sm", s.state === "current" ? "font-semibold text-ink" : "text-ink-2")}>
              {s.label}
              {s.state === "complete" ? <span className="sr-only"> ({labels.completed})</span> : null}
            </span>
            {i < steps.length - 1 ? <span aria-hidden className="mx-1 hidden h-px w-8 bg-line-strong sm:block" /> : null}
          </li>
        ))}
      </ol>
    </nav>
  );
}
