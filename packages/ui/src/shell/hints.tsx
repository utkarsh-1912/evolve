"use client";
// Clean-UI helpers (docs/09 §10): IconAction (secondary action = IconButton + tooltip), ContextChip (icon + 1–2 words,
// detail in tooltip AND in screen-reader text), SimulatedMark (the one small flask badge per surface).
// Tooltips are supplementary: everything they say is also in the accessible name/description.
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { FlaskConical, type LucideIcon } from "lucide-react";
import { forwardRef, useId, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";

function Tip({ content, children, side = "top" }: { content: ReactNode; children: ReactNode; side?: "top" | "bottom" }) {
  return (
    <TooltipPrimitive.Root delayDuration={200}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content side={side} sideOffset={6} className="z-50 max-w-xs rounded-md bg-[#0a1225] px-3 py-1.5 text-sm text-[#fffef0] shadow-e2">
          {content}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

/** Secondary action: icon-only button with aria-label + tooltip. Never for primary or safety-critical actions (§10). */
export const IconAction = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { label: string; icon: LucideIcon; variant?: "ghost" | "secondary" | "inverse"; tipSide?: "top" | "bottom" }
>(function IconAction({ label, icon: Icon, variant = "ghost", tipSide = "top", className, ...props }, ref) {
  return (
    <Tip content={label} side={tipSide}>
      <button
        ref={ref}
        type="button"
        aria-label={label}
        className={cn(
          "relative inline-grid size-11 shrink-0 place-items-center rounded-md transition-colors duration-[var(--motion-fast)] disabled:opacity-50 [&_svg]:size-5",
          variant === "ghost" && "text-ink hover:bg-surface-2",
          variant === "secondary" && "border border-line-strong bg-surface-1 text-ink hover:border-navy",
          variant === "inverse" && "text-cream hover:bg-white/10",
          className,
        )}
        {...props}
      >
        <Icon aria-hidden />
      </button>
    </Tip>
  );
});

/** Context chip: short visible label, full detail in tooltip + sr-only text (keyboard focusable). */
export function ContextChip({
  icon: Icon,
  label,
  detail,
  tone = "neutral",
  testId,
}: {
  icon: LucideIcon;
  label: ReactNode;
  detail?: ReactNode;
  tone?: "neutral" | "info" | "review";
  testId?: string;
}) {
  const id = useId();
  const chip = (
    <span
      tabIndex={detail ? 0 : undefined}
      aria-describedby={detail ? id : undefined}
      data-testid={testId}
      data-status={tone}
      className={cn(
        "inline-flex min-h-8 items-center gap-1.5 rounded-full border px-2.5 text-xs font-semibold [&_svg]:size-3.5",
        tone === "neutral" && "border-line-strong bg-surface-1 text-ink",
        tone === "info" && "border-info/50 bg-info/10 text-info-ink",
        tone === "review" && "border-review bg-review/15 text-review-ink",
      )}
    >
      <Icon aria-hidden />
      {label}
      {detail ? (
        <span id={id} className="sr-only">
          {detail}
        </span>
      ) : null}
    </span>
  );
  return detail ? <Tip content={detail} side="bottom">{chip}</Tip> : chip;
}

/** The single per-surface SIMULATED marker: flask icon + short word, tooltip explains (banner carries the full text). */
export function SimulatedMark({ label, detail, className }: { label?: string; detail?: string; className?: string }) {
  const { labels } = useUI();
  const id = useId();
  return (
    <Tip content={detail ?? labels.simulatedDetail}>
      <span
        tabIndex={0}
        data-simulated="true"
        aria-describedby={id}
        className={cn("inline-flex min-h-7 items-center gap-1 rounded-sm border border-dashed border-navy/50 px-1.5 text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-navy", className)}
      >
        <FlaskConical aria-hidden className="size-3.5" />
        {label ?? labels.simulated}
        <span id={id} className="sr-only">
          {detail ?? labels.simulatedDetail}
        </span>
      </span>
    </Tip>
  );
}
