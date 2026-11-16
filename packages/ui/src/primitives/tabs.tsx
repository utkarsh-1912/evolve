"use client";
// Tabs, Stepper, Accordion, Breadcrumbs, Pagination.
import * as TabsPrimitive from "@radix-ui/react-tabs";

import type { ReactNode } from "react";

import { useUI } from "../provider";

/** Tabs (Radix): roving focus, arrow keys mirror in RTL. */

export function Tabs({
  tabs,
  defaultValue,
  value,
  onValueChange,
  label,
}: {
  tabs: { value: string; label: ReactNode; content: ReactNode; count?: number }[];
  defaultValue?: string;
  value?: string;
  onValueChange?: (v: string) => void;
  label: string;
}) {
  const { dir } = useUI();
  return (
    <TabsPrimitive.Root dir={dir} defaultValue={defaultValue ?? tabs[0]?.value} value={value} onValueChange={onValueChange}>
      <TabsPrimitive.List aria-label={label} className="flex gap-1 overflow-x-auto border-b border-line">
        {tabs.map((t) => (
          <TabsPrimitive.Trigger
            key={t.value}
            value={t.value}
            className="relative -mb-px inline-flex min-h-11 items-center gap-2 whitespace-nowrap border-b-2 border-transparent px-4 text-sm font-semibold text-ink-2 hover:text-ink data-[state=active]:border-navy data-[state=active]:text-ink [[data-theme=ledger]_&]:data-[state=active]:border-lime"
          >
            {t.label}
            {typeof t.count === "number" ? (
              <span className="rounded-full bg-surface-2 px-2 text-xs text-ink">{t.count}</span>
            ) : null}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
      {tabs.map((t) => (
        <TabsPrimitive.Content key={t.value} value={t.value} className="pt-5">
          {t.content}
        </TabsPrimitive.Content>
      ))}
    </TabsPrimitive.Root>
  );
}
