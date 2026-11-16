"use client";
// Toast (Radix): polite announcements for completed actions. Never the only record of something important.
import * as ToastPrimitive from "@radix-ui/react-toast";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";

export interface ToastInput {
  title: ReactNode;
  description?: ReactNode;
  tone?: "info" | "success" | "danger";
}
interface ToastItem extends ToastInput {
  id: number;
}

const ToastContext = createContext<(t: ToastInput) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const { labels, dir } = useUI();
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((t: ToastInput) => setItems((xs) => [...xs, { ...t, id: Date.now() + Math.random() }]), []);
  return (
    <ToastContext.Provider value={push}>
      <ToastPrimitive.Provider swipeDirection={dir === "rtl" ? "left" : "right"} duration={6000}>
        {children}
        {items.map((t) => {
          const Icon = t.tone === "success" ? CheckCircle2 : t.tone === "danger" ? XCircle : Info;
          return (
            <ToastPrimitive.Root
              key={t.id}
              type={t.tone === "danger" ? "foreground" : "background"}
              onOpenChange={(o) => !o && setItems((xs) => xs.filter((x) => x.id !== t.id))}
              className={cn(
                "flex items-start gap-3 rounded-lg border bg-surface-3 p-4 text-ink shadow-e3 data-[state=open]:animate-[toast-in_var(--motion-slow)_var(--ease-out)]",
                t.tone === "success" && "border-compatible/60",
                t.tone === "danger" && "border-escalated/60",
                (!t.tone || t.tone === "info") && "border-line",
              )}
            >
              <Icon
                aria-hidden
                className={cn(
                  "mt-0.5 size-5 shrink-0",
                  t.tone === "success" ? "text-compatible-ink" : t.tone === "danger" ? "text-escalated-ink" : "text-info-ink",
                )}
              />
              <div className="min-w-0 flex-1">
                <ToastPrimitive.Title className="font-semibold">{t.title}</ToastPrimitive.Title>
                {t.description ? <ToastPrimitive.Description className="text-sm text-ink-2">{t.description}</ToastPrimitive.Description> : null}
              </div>
              <ToastPrimitive.Close aria-label={labels.close} className="-m-2 grid size-11 place-items-center rounded-md text-ink-2 hover:bg-surface-2">
                <X aria-hidden className="size-4" />
              </ToastPrimitive.Close>
            </ToastPrimitive.Root>
          );
        })}
        <ToastPrimitive.Viewport className="fixed bottom-20 end-4 z-[60] flex w-[min(92vw,24rem)] flex-col gap-2 outline-none md:bottom-6" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}

/** Static toast look for the style guide (no timers). */
export function ToastPreview({ title, description, tone = "info" }: ToastInput) {
  const Icon = tone === "success" ? CheckCircle2 : tone === "danger" ? XCircle : Info;
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border bg-surface-3 p-4 text-ink shadow-e3",
        tone === "success" ? "border-compatible/60" : tone === "danger" ? "border-escalated/60" : "border-line",
      )}
    >
      <Icon aria-hidden className={cn("mt-0.5 size-5 shrink-0", tone === "success" ? "text-compatible-ink" : tone === "danger" ? "text-escalated-ink" : "text-info-ink")} />
      <div>
        <p className="font-semibold">{title}</p>
        {description ? <p className="text-sm text-ink-2">{description}</p> : null}
      </div>
    </div>
  );
}
