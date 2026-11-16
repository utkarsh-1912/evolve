"use client";
// Tabs, Stepper, Accordion, Breadcrumbs, Pagination.
import * as AccordionPrimitive from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";
import type { ReactNode } from "react";

import { useUI } from "../provider";

/** Tabs (Radix): roving focus, arrow keys mirror in RTL. */

/** Accordion (Radix). */
export function Accordion({
  items,
  type = "single",
  defaultValue,
}: {
  items: { value: string; title: ReactNode; content: ReactNode }[];
  type?: "single" | "multiple";
  defaultValue?: string;
}) {
  const { dir } = useUI();
  const inner = items.map((it) => (
    <AccordionPrimitive.Item key={it.value} value={it.value} className="border-b border-line last:border-b-0">
      <AccordionPrimitive.Header>
        <AccordionPrimitive.Trigger className="group flex min-h-12 w-full items-center justify-between gap-3 py-3 text-start font-semibold text-ink">
          {it.title}
          <ChevronDown aria-hidden className="size-5 shrink-0 text-ink-2 transition-transform duration-[var(--motion-base)] group-data-[state=open]:rotate-180" />
        </AccordionPrimitive.Trigger>
      </AccordionPrimitive.Header>
      <AccordionPrimitive.Content className="pb-4 text-ink">{it.content}</AccordionPrimitive.Content>
    </AccordionPrimitive.Item>
  ));
  return type === "single" ? (
    <AccordionPrimitive.Root dir={dir} type="single" collapsible defaultValue={defaultValue} className="rounded-lg border border-line bg-surface-1 px-4">
      {inner}
    </AccordionPrimitive.Root>
  ) : (
    <AccordionPrimitive.Root dir={dir} type="multiple" defaultValue={defaultValue ? [defaultValue] : undefined} className="rounded-lg border border-line bg-surface-1 px-4">
      {inner}
    </AccordionPrimitive.Root>
  );
}
