"use client";
// Collapsible icon rail (docs/09 §10.1, DECISIONS #52): collapsed 72 px (mark + icons) by default on ≤1440 px,
// expanded 240 px on wider screens; the viewer's choice is remembered (localStorage, try/catch). Every item has an
// aria-label and a Radix Tooltip (hover + keyboard focus) while collapsed; the active item keeps the lime indicator.
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useCallback, useId, useSyncExternalStore, type ReactNode } from "react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";
import type { NavItem } from "./app-shell";

const listeners = new Set<() => void>();
const WIDE = "(min-width: 1441px)";

function readPref(key: string): boolean | null {
  try {
    const v = window.localStorage.getItem(key);
    return v === null ? null : v === "1";
  } catch {
    return null;
  }
}

/** Collapsed state: stored preference, else viewport default (collapsed on ≤1440 px). Server render = collapsed. */
export function useRailCollapsed(storageKey = "evolve.rail.collapsed") {
  const subscribe = useCallback((cb: () => void) => {
    listeners.add(cb);
    const mq = window.matchMedia(WIDE);
    mq.addEventListener("change", cb);
    window.addEventListener("storage", cb);
    return () => {
      listeners.delete(cb);
      mq.removeEventListener("change", cb);
      window.removeEventListener("storage", cb);
    };
  }, []);
  const collapsed = useSyncExternalStore(
    subscribe,
    () => readPref(storageKey) ?? !window.matchMedia(WIDE).matches,
    () => true,
  );
  const setCollapsed = useCallback(
    (v: boolean) => {
      try {
        window.localStorage.setItem(storageKey, v ? "1" : "0");
      } catch {
        /* storage unavailable: state still applies for this render via listeners */
      }
      listeners.forEach((l) => l());
    },
    [storageKey],
  );
  return [collapsed, setCollapsed] as const;
}

function RailTip({ label, show, children }: { label: string; show: boolean; children: ReactNode }) {
  const { dir } = useUI();
  if (!show) return <>{children}</>;
  return (
    <TooltipPrimitive.Root delayDuration={150}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={dir === "rtl" ? "left" : "right"}
          sideOffset={10}
          className="z-50 rounded-md bg-[#0a1225] px-3 py-1.5 text-sm font-medium text-[#fffef0] shadow-e2"
        >
          {label}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

export function Rail({
  logo,
  mark,
  items,
  storageKey,
}: {
  /** Full lockup (expanded) and icon-only mark (collapsed), both for a navy surface. */
  logo: ReactNode;
  mark: ReactNode;
  items: NavItem[];
  storageKey?: string;
}) {
  const { labels, Link } = useUI();
  const [collapsed, setCollapsed] = useRailCollapsed(storageKey);
  const navId = useId();
  const ToggleIcon = collapsed ? PanelLeftOpen : PanelLeftClose;
  const toggleLabel = collapsed ? labels.expandMenu : labels.collapseMenu;
  return (
    <aside
      data-testid="sidebar"
      data-collapsed={collapsed}
      className={cn(
        "hidden shrink-0 self-stretch bg-navy text-cream transition-[width] duration-[var(--motion-base)] md:block",
        collapsed ? "w-[72px]" : "w-[240px]",
      )}
    >
      <div className="sticky top-0 flex h-dvh flex-col">
        <div className={cn("flex h-16 items-center", collapsed ? "justify-center" : "px-4")}>{collapsed ? mark : logo}</div>
        <nav id={navId} aria-label={labels.mainNav} className="flex-1 overflow-y-auto px-2 py-2">
          <ul className="space-y-1">
            {items.map((it) => {
              const Icon = it.icon;
              return (
                <li key={it.key}>
                  <RailTip label={it.label} show={collapsed}>
                    <Link
                      href={it.href}
                      aria-label={collapsed ? it.label : undefined}
                      aria-current={it.active ? "page" : undefined}
                      data-testid={`rail-${it.key}`}
                      className={cn(
                        "relative flex min-h-11 items-center gap-3 rounded-md text-[0.9375rem]",
                        collapsed ? "justify-center px-0" : "px-3",
                        it.active ? "bg-white/12 font-semibold text-cream" : "text-cream/90 hover:bg-white/8 hover:text-cream",
                      )}
                    >
                      {it.active ? <span aria-hidden className="absolute inset-y-2 start-0 w-1 rounded-full bg-lime" /> : null}
                      <Icon aria-hidden className="size-5 shrink-0" />
                      {collapsed ? null : <span className="flex-1 truncate">{it.label}</span>}
                      {it.badge && !collapsed ? <span className="rounded-full bg-lime px-2 text-xs font-bold text-navy">{it.badge}</span> : null}
                    </Link>
                  </RailTip>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className={cn("border-t border-white/10 p-2", collapsed ? "flex justify-center" : "")}>
          <RailTip label={toggleLabel} show>
            <button
              type="button"
              onClick={() => setCollapsed(!collapsed)}
              aria-expanded={!collapsed}
              aria-controls={navId}
              aria-label={toggleLabel}
              data-testid="rail-toggle"
              className="grid size-11 place-items-center rounded-md text-cream/90 hover:bg-white/8"
            >
              <ToggleIcon aria-hidden className="size-5 rtl:-scale-x-100" />
            </button>
          </RailTip>
        </div>
      </div>
    </aside>
  );
}
