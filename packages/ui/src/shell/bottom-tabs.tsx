"use client";
// Role-based app shell (docs/09 §3): Sidebar (264px) + TopBar + ContextStrip + main + ShellFooter;
// mobile (<768px): TopBar + BottomTabs (+ "More" drawer). Logical properties throughout (RTL-safe).
import { NavEntry, type NavItem } from "./app-shell";
import { MoreHorizontal } from "lucide-react";
import { useState } from "react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";

import { Drawer } from "../primitives/dialog";

export function BottomTabs({ items, more }: { items: NavItem[]; more?: NavItem[] }) {
  const { labels } = useUI();
  const { Link } = useUI();
  const [open, setOpen] = useState(false);
  const moreActive = more?.some((m) => m.active);
  const tab = "flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-[0.6875rem] font-semibold";
  return (
    <nav aria-label={labels.mainNav} className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface-1 pb-[env(safe-area-inset-bottom)] md:hidden" data-testid="bottom-tabs">
      <ul className="flex">
        {items.map((it) => {
          const Icon = it.icon;
          return (
            <li key={it.key} className="flex flex-1">
              {it.disabled ? (
                <span aria-disabled="true" className={cn(tab, "text-ink-2/70")}>
                  <Icon aria-hidden className="size-5" />
                  {it.label}
                </span>
              ) : (
                <Link href={it.href} aria-current={it.active ? "page" : undefined} className={cn(tab, it.active ? "text-navy" : "text-ink-2")}>
                  <span className={cn("grid h-7 w-12 place-items-center rounded-full", it.active && "bg-navy text-cream")}>
                    <Icon aria-hidden className="size-5" />
                  </span>
                  {it.label}
                </Link>
              )}
            </li>
          );
        })}
        {more && more.length ? (
          <li className="flex flex-1">
            <Drawer
              open={open}
              onOpenChange={setOpen}
              side="bottom"
              title={labels.more}
              trigger={
                <button type="button" className={cn(tab, moreActive ? "text-navy" : "text-ink-2")} aria-current={moreActive ? "page" : undefined}>
                  <span className={cn("grid h-7 w-12 place-items-center rounded-full", moreActive && "bg-navy text-cream")}>
                    <MoreHorizontal aria-hidden className="size-5" />
                  </span>
                  {labels.more}
                </button>
              }
            >
              <ul className="space-y-1" onClick={() => setOpen(false)}>
                {more.map((it) => (
                  <li key={it.key}>
                    <NavEntry item={it} variant="drawer" />
                  </li>
                ))}
              </ul>
            </Drawer>
          </li>
        ) : null}
      </ul>
    </nav>
  );
}
