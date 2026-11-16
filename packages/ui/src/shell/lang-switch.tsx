"use client";
// LangSwitch (§10.2): compact = globe icon with accessible name + tooltip (top bar); text variant for headers.
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { Globe } from "lucide-react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";

export function LangSwitch({ href, label, lang, compact, className }: { href: string; label: string; lang: string; compact?: boolean; className?: string }) {
  const { labels } = useUI();
  const link = (
    <a
      href={href}
      hrefLang={lang}
      aria-label={`${labels.language}: ${label}`}
      className={cn("inline-flex min-h-11 items-center gap-2 rounded-md text-sm font-semibold text-ink hover:bg-surface-2", compact ? "size-11 justify-center" : "px-3", className)}
      data-testid="lang-switch"
    >
      <Globe aria-hidden className="size-5" />
      {compact ? null : <span lang={lang}>{label}</span>}
    </a>
  );
  if (!compact) return link;
  return (
    <TooltipPrimitive.Root delayDuration={200}>
      <TooltipPrimitive.Trigger asChild>{link}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content side="bottom" sideOffset={6} className="z-50 rounded-md bg-[#0a1225] px-3 py-1.5 text-sm text-[#fffef0] shadow-e2">
          <span lang={lang}>{label}</span>
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
