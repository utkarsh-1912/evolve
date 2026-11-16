"use client";
// Tabs, Stepper, Accordion, Breadcrumbs, Pagination.
import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

import { useUI } from "../provider";

/** Tabs (Radix): roving focus, arrow keys mirror in RTL. */

/** Breadcrumbs: last item is the current page (not a link). Chevrons mirror in RTL. */
export function Breadcrumbs({ items }: { items: { label: ReactNode; href?: string }[] }) {
  const { labels, Link } = useUI();
  return (
    <nav aria-label={labels.breadcrumb}>
      <ol className="flex flex-wrap items-center gap-1 text-sm text-ink-2">
        {items.map((it, i) => {
          const last = i === items.length - 1;
          return (
            <li key={i} className="flex items-center gap-1">
              {it.href && !last ? (
                <Link href={it.href} className="rounded-sm underline-offset-4 hover:text-ink hover:underline">
                  {it.label}
                </Link>
              ) : (
                <span aria-current={last ? "page" : undefined} className={last ? "font-medium text-ink" : undefined}>
                  {it.label}
                </span>
              )}
              {!last ? <ChevronRight aria-hidden className="size-4 rtl:-scale-x-100" /> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
