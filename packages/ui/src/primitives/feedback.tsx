"use client";
// State matrix (docs/09 §6): Alert, EmptyState, Skeleton, ErrorState, OfflineBanner, StaleNotice,
// PermissionState, GuardBanner ("Held for counselor review"), EnvironmentBanner (replaces StatusBanner, A7).
import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle, CheckCircle2, FlaskConical, Info, KeyRound, RefreshCw, ShieldAlert, WifiOff, XCircle, type LucideIcon } from "lucide-react";
import { useId, useSyncExternalStore, type ReactNode } from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "../lib/cn";
import { useUI } from "../provider";
import { Button } from "./button";

const alertVariants = cva("flex gap-3 rounded-lg border p-4 text-ink [&>svg]:mt-0.5 [&>svg]:size-5 [&>svg]:shrink-0", {
  variants: {
    tone: {
      info: "border-info/40 bg-info/5 [&>svg]:text-info-ink",
      success: "border-compatible/50 bg-compatible/5 [&>svg]:text-compatible-ink",
      warning: "border-review/60 bg-review/10 [&>svg]:text-review-ink",
      danger: "border-escalated/60 bg-escalated/5 [&>svg]:text-escalated-ink",
    },
  },
  defaultVariants: { tone: "info" },
});

const ALERT_ICON: Record<"info" | "success" | "warning" | "danger", LucideIcon> = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
};

/** Alert: info / success / warning / danger. danger uses role=alert; others are status. */
export function Alert({
  tone = "info",
  title,
  children,
  action,
  className,
  icon,
  testId,
}: VariantProps<typeof alertVariants> & {
  title?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
  icon?: LucideIcon;
  testId?: string;
}) {
  const t = tone ?? "info";
  const Icon = icon ?? ALERT_ICON[t];
  return (
    <div role={t === "danger" ? "alert" : "status"} className={cn(alertVariants({ tone }), className)} data-testid={testId}>
      <Icon aria-hidden />
      <div className="min-w-0 flex-1 space-y-1">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? <div className="text-sm text-ink">{children}</div> : null}
        {action ? <div className="pt-2">{action}</div> : null}
      </div>
    </div>
  );
}

/** EmptyState: illustration-free, one action (docs/09 §6). */
export function EmptyState({
  icon: Icon = Info,
  title,
  body,
  action,
  className,
  testId,
}: {
  icon?: LucideIcon;
  title: ReactNode;
  body?: ReactNode;
  action?: ReactNode;
  className?: string;
  testId?: string;
}) {
  return (
    <div
      data-testid={testId}
      className={cn("flex flex-col items-center gap-3 rounded-xl border border-dashed border-line-strong px-6 py-10 text-center", className)}
    >
      <span className="grid size-12 place-items-center rounded-full bg-surface-2 text-navy">
        <Icon aria-hidden className="size-6" />
      </span>
      <p className="text-base font-semibold text-ink">{title}</p>
      {body ? <p className="max-w-[52ch] text-sm text-ink-2">{body}</p> : null}
      {action ? <div className="pt-1">{action}</div> : null}
    </div>
  );
}

/** Skeleton block. Compose to match the layout being loaded (no spinners for long waits). */
export function Skeleton({ className, rounded = "md" }: { className?: string; rounded?: "sm" | "md" | "lg" | "full" }) {
  return (
    <span
      aria-hidden
      className={cn(
        "skeleton block bg-surface-2",
        rounded === "sm" && "rounded-sm",
        rounded === "md" && "rounded-md",
        rounded === "lg" && "rounded-lg",
        rounded === "full" && "rounded-full",
        className,
      )}
    />
  );
}

/** Screen-reader announcement + skeleton children. */
export function LoadingRegion({ children, label }: { children: ReactNode; label?: string }) {
  const { labels } = useUI();
  return (
    <div role="status" aria-busy="true" aria-live="polite">
      <span className="sr-only">{label ?? labels.loading}</span>
      {children}
    </div>
  );
}

/** ErrorState: retry + reference ID; never PHI or genes in the message. */
export function ErrorState({
  title,
  body,
  reference,
  onRetry,
  className,
}: {
  title?: ReactNode;
  body?: ReactNode;
  reference?: string;
  onRetry?: () => void;
  className?: string;
}) {
  const { labels } = useUI();
  return (
    <div role="alert" className={cn("flex flex-col items-start gap-3 rounded-xl border border-escalated/50 bg-escalated/5 p-5", className)}>
      <p className="flex items-center gap-2 font-semibold text-ink">
        <XCircle aria-hidden className="size-5 text-escalated-ink" />
        {title ?? labels.errorTitle}
      </p>
      <p className="text-sm text-ink">{body ?? labels.errorBody}</p>
      {reference ? (
        <p className="text-xs text-ink-2">
          {labels.errorReference}: <span className="font-mono">{reference}</span>
        </p>
      ) : null}
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry} leadingIcon={<RefreshCw aria-hidden />}>
          {labels.retry}
        </Button>
      ) : null}
    </div>
  );
}

function subscribeOnline(cb: () => void) {
  window.addEventListener("online", cb);
  window.addEventListener("offline", cb);
  return () => {
    window.removeEventListener("online", cb);
    window.removeEventListener("offline", cb);
  };
}

/** OfflineBanner: renders only while the browser reports offline (or when forced, for the style guide). */
export function OfflineBanner({ force }: { force?: boolean }) {
  const { labels } = useUI();
  const online = useSyncExternalStore(subscribeOnline, () => navigator.onLine, () => true);
  if (online && !force) return null;
  return (
    <div role="status" className="flex items-center gap-2 bg-neutral-900 px-4 py-2 text-sm text-neutral-50" data-testid="offline-banner">
      <WifiOff aria-hidden className="size-4" />
      {labels.offline}
    </div>
  );
}

/** StaleNotice: data older than the session → "Refresh". */
export function StaleNotice({ onRefresh, children }: { onRefresh: () => void; children?: ReactNode }) {
  const { labels } = useUI();
  return (
    <Alert
      tone="warning"
      icon={RefreshCw}
      title={children ?? labels.stale}
      action={
        <Button variant="secondary" size="sm" onClick={onRefresh}>
          {labels.refresh}
        </Button>
      }
    />
  );
}

/** PermissionState: explains the consent needed instead of a bare 403. */
export function PermissionState({ body, action }: { body: ReactNode; action?: ReactNode }) {
  const { labels } = useUI();
  return <EmptyState icon={KeyRound} title={labels.permissionTitle} body={body} action={action} />;
}

/** GuardBanner: partial state. A gate-held message is never shown; this explains why (P-18). */
export function GuardBanner({ title, children, testId }: { title?: ReactNode; children?: ReactNode; testId?: string }) {
  const { labels } = useUI();
  return (
    <div data-testid={testId} role="status" className="flex gap-3 rounded-lg border border-review/60 bg-review/10 p-4">
      <ShieldAlert aria-hidden className="mt-0.5 size-5 shrink-0 text-review-ink" />
      <div className="space-y-1">
        <p className="font-semibold text-ink">{title ?? labels.heldForReview}</p>
        <div className="text-sm text-ink">{children ?? labels.heldForReviewBody}</div>
      </div>
    </div>
  );
}

/** Notice: neutral, non-signal statement (e.g. the judicial "certificate regardless" line, P-14). */
export function Notice({ children, icon: Icon = Info, testId, className }: { children: ReactNode; icon?: LucideIcon; testId?: string; className?: string }) {
  return (
    <p data-testid={testId} className={cn("flex items-start gap-3 rounded-lg bg-surface-2 p-4 font-medium text-ink", className)}>
      <Icon aria-hidden className="mt-0.5 size-5 shrink-0 text-navy" />
      <span>{children}</span>
    </p>
  );
}

/** EnvironmentBanner: the ONE global environment notice (replaces StatusBanner; A7). */
export function EnvironmentBanner({ label, detail }: { label: ReactNode; detail?: ReactNode }) {
  return (
    // Fixed, theme-independent colors: the Ledger neutral ramp is inverted (REQUEST-UI-1 from instance C).
    <div role="region" aria-label="Environment" className="bg-[#0a1225] text-[#fffef0] [[data-theme=ledger]_&]:bg-black [[data-theme=ledger]_&]:text-[#e9e8e4]">
      <p className="mx-auto flex max-w-[var(--content-max)] flex-wrap items-center justify-center gap-x-3 gap-y-0.5 px-4 py-1.5 text-center text-xs">
        <span className="inline-flex items-center gap-1.5 font-semibold uppercase tracking-[0.08em]">
          <FlaskConical aria-hidden className="size-3.5" />
          {label}
        </span>
        {detail ? <span className="text-[#c9d1de] [[data-theme=ledger]_&]:text-[#c9c8c2]">{detail}</span> : null}
      </p>
    </div>
  );
}

/** SimulatedBadge (§10.4): the ONE small flask marker per surface, with tooltip; the global banner carries the full text. */
export function SimulatedBadge({ label, className }: { label?: string; className?: string }) {
  const { labels } = useUI();
  const id = useId();
  return (
    <TooltipPrimitive.Root delayDuration={200}>
      <TooltipPrimitive.Trigger asChild>
        <span
          tabIndex={0}
          data-simulated="true"
          aria-describedby={id}
          className={cn(
            "inline-flex min-h-7 items-center gap-1 rounded-sm border border-dashed border-navy/50 px-1.5 text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-navy",
            className,
          )}
        >
          <FlaskConical aria-hidden className="size-3.5" />
          {label ?? labels.simulated}
          <span id={id} className="sr-only">
            {labels.simulatedDetail}
          </span>
        </span>
      </TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content sideOffset={6} className="z-50 max-w-xs rounded-md bg-[#0a1225] px-3 py-1.5 text-sm text-[#fffef0] shadow-e2">
          {labels.simulatedDetail}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
