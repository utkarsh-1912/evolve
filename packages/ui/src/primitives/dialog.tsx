"use client";
// Overlays on Radix: Dialog, ConfirmDialog (A6), Drawer, Tooltip, DropdownMenu, Popover.
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { AlertTriangle, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";
import { Button } from "./button";

const overlayCls =
  "fixed inset-0 z-50 bg-overlay data-[state=open]:animate-[fade-in_var(--motion-base)_var(--ease-standard)] data-[state=closed]:animate-[fade-out_var(--motion-fast)_var(--ease-standard)]";

export interface DialogProps {
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (o: boolean) => void;
  trigger?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg";
  testId?: string;
}

/** Dialog: modal, focus-trapped, Esc to close, labelled by its title. */
export function Dialog({ open, defaultOpen, onOpenChange, trigger, title, description, children, footer, size = "md", testId }: DialogProps) {
  const { labels, dir } = useUI();
  return (
    <DialogPrimitive.Root open={open} defaultOpen={defaultOpen} onOpenChange={onOpenChange}>
      {trigger ? <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger> : null}
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className={overlayCls} />
        <DialogPrimitive.Content
          dir={dir}
          data-testid={testId}
          className={cn(
            "fixed start-1/2 top-1/2 z-50 grid max-h-[calc(100dvh-2rem)] w-[calc(100vw-2rem)] -translate-y-1/2 gap-4 overflow-y-auto rounded-xl bg-surface-3 p-6 text-ink shadow-e3 ltr:-translate-x-1/2 rtl:translate-x-1/2",
            size === "sm" && "max-w-md",
            size === "md" && "max-w-lg",
            size === "lg" && "max-w-2xl",
          )}
        >
          <div className="space-y-1.5 pe-10">
            <DialogPrimitive.Title className="text-xl font-semibold leading-snug">{title}</DialogPrimitive.Title>
            {description ? (
              <DialogPrimitive.Description className="text-sm text-ink-2">{description}</DialogPrimitive.Description>
            ) : (
              <DialogPrimitive.Description className="sr-only">{typeof title === "string" ? title : ""}</DialogPrimitive.Description>
            )}
          </div>
          {children}
          {footer ? <div className="flex flex-wrap justify-end gap-2 pt-2">{footer}</div> : null}
          <DialogPrimitive.Close asChild>
            <button
              type="button"
              aria-label={labels.close}
              className="absolute end-3 top-3 grid size-11 place-items-center rounded-md text-ink-2 hover:bg-surface-2 hover:text-ink"
            >
              <X aria-hidden className="size-5" />
            </button>
          </DialogPrimitive.Close>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

/**
 * ConfirmDialog: destructive actions state their consequences before anything happens (A6).
 * Focus starts on Cancel (the safe choice); confirm shows a loading state while the action runs.
 */
export function ConfirmDialog({
  trigger,
  open,
  onOpenChange,
  title,
  description,
  consequences,
  confirmLabel,
  cancelLabel,
  onConfirm,
  tone = "danger",
  testId,
}: {
  trigger?: ReactNode;
  open?: boolean;
  onOpenChange?: (o: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  consequences?: ReactNode[];
  confirmLabel: ReactNode;
  cancelLabel?: ReactNode;
  onConfirm: () => Promise<void> | void;
  tone?: "danger" | "primary";
  testId?: string;
}) {
  const { labels } = useUI();
  const [internalOpen, setInternalOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const isOpen = open ?? internalOpen;
  const setOpen = (o: boolean) => {
    if (busy) return;
    setInternalOpen(o);
    onOpenChange?.(o);
  };
  return (
    <DialogPrimitive.Root open={isOpen} onOpenChange={setOpen}>
      {trigger ? <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger> : null}
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className={overlayCls} />
        <DialogPrimitive.Content
          role="alertdialog"
          data-testid={testId}
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            (document.querySelector("[data-confirm-cancel]") as HTMLElement | null)?.focus();
          }}
          className="fixed start-1/2 top-1/2 z-50 grid w-[calc(100vw-2rem)] max-w-md -translate-y-1/2 gap-4 rounded-xl bg-surface-3 p-6 text-ink shadow-e3 ltr:-translate-x-1/2 rtl:translate-x-1/2"
        >
          <div className="flex gap-3">
            {tone === "danger" ? (
              <span className="grid size-10 shrink-0 place-items-center rounded-full bg-escalated/10 text-escalated-ink">
                <AlertTriangle aria-hidden className="size-5" />
              </span>
            ) : null}
            <div className="space-y-1.5">
              <DialogPrimitive.Title className="text-lg font-semibold leading-snug">{title}</DialogPrimitive.Title>
              <DialogPrimitive.Description className="text-sm text-ink-2">{description ?? ""}</DialogPrimitive.Description>
            </div>
          </div>
          {consequences && consequences.length ? (
            <div className="rounded-lg bg-surface-2 p-4">
              <p className="mb-2 text-sm font-semibold">{labels.consequences}</p>
              <ul className="list-disc space-y-1 ps-5 text-sm">
                {consequences.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <DialogPrimitive.Close asChild>
              <Button variant="secondary" data-confirm-cancel disabled={busy}>
                {cancelLabel ?? labels.cancel}
              </Button>
            </DialogPrimitive.Close>
            <Button
              variant={tone === "danger" ? "danger" : "primary"}
              loading={busy}
              data-testid={testId ? `${testId}-confirm` : undefined}
              onClick={async () => {
                setBusy(true);
                try {
                  await onConfirm();
                  setInternalOpen(false);
                  onOpenChange?.(false);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {confirmLabel}
            </Button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

/** Drawer: side sheet (end side; mirrors in RTL). Used for detail panes and the mobile "More" menu. */
export function Drawer({
  open,
  onOpenChange,
  trigger,
  title,
  description,
  children,
  side = "end",
  testId,
}: {
  open?: boolean;
  onOpenChange?: (o: boolean) => void;
  trigger?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  side?: "end" | "bottom";
  testId?: string;
}) {
  const { labels, dir } = useUI();
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      {trigger ? <DialogPrimitive.Trigger asChild>{trigger}</DialogPrimitive.Trigger> : null}
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className={overlayCls} />
        <DialogPrimitive.Content
          dir={dir}
          data-testid={testId}
          className={cn(
            "fixed z-50 flex flex-col gap-4 overflow-y-auto bg-surface-3 p-6 text-ink shadow-e3",
            side === "end" && "inset-y-0 end-0 w-[min(100vw,28rem)] data-[state=open]:animate-[drawer-in_var(--motion-slow)_var(--ease-out)]",
            side === "bottom" && "inset-x-0 bottom-0 max-h-[85dvh] rounded-t-xl data-[state=open]:animate-[sheet-in_var(--motion-slow)_var(--ease-out)]",
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <DialogPrimitive.Title className="text-lg font-semibold">{title}</DialogPrimitive.Title>
              <DialogPrimitive.Description className={cn("text-sm text-ink-2", !description && "sr-only")}>
                {description ?? (typeof title === "string" ? title : "")}
              </DialogPrimitive.Description>
            </div>
            <DialogPrimitive.Close asChild>
              <button type="button" aria-label={labels.close} className="grid size-11 shrink-0 place-items-center rounded-md text-ink-2 hover:bg-surface-2">
                <X aria-hidden className="size-5" />
              </button>
            </DialogPrimitive.Close>
          </div>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
