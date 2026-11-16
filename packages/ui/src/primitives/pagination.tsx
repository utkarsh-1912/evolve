"use client";
// Tabs, Stepper, Accordion, Breadcrumbs, Pagination.
import { ChevronLeft, ChevronRight } from "lucide-react";

import { fmt, useUI } from "../provider";

/** Tabs (Radix): roving focus, arrow keys mirror in RTL. */

/** Pagination: previous / "page of pages" / next. */
export function Pagination({
  page,
  pages,
  onPage,
}: {
  page: number; // 1-based
  pages: number;
  onPage: (p: number) => void;
}) {
  const { labels } = useUI();
  if (pages <= 1) return null;
  const btn =
    "inline-flex min-h-11 items-center gap-1 rounded-md border border-line-strong bg-surface-1 px-3 text-sm font-semibold text-ink hover:border-navy disabled:pointer-events-none disabled:opacity-50";
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-3">
      <button type="button" className={btn} onClick={() => onPage(page - 1)} disabled={page <= 1}>
        <ChevronLeft aria-hidden className="size-4 rtl:-scale-x-100" />
        {labels.previous}
      </button>
      <p className="text-sm text-ink-2" aria-live="polite">
        {fmt(labels.pageOf, { page, pages })}
      </p>
      <button type="button" className={btn} onClick={() => onPage(page + 1)} disabled={page >= pages}>
        {labels.next}
        <ChevronRight aria-hidden className="size-4 rtl:-scale-x-100" />
      </button>
    </nav>
  );
}
