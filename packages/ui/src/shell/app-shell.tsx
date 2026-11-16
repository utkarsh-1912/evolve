"use client";
// Role-based app shell (docs/09 §3): Sidebar (264px) + TopBar + ContextStrip + main + ShellFooter;
// mobile (<768px): TopBar + BottomTabs (+ "More" drawer). Logical properties throughout (RTL-safe).
import { type LucideIcon } from "lucide-react";
import { type ReactNode } from "react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";

import { Breadcrumbs } from "../primitives/breadcrumbs";

export interface NavItem {
  key: string;
  href: string;
  label: string;
  icon: LucideIcon;
  active?: boolean;
  /** Not yet available: rendered as non-interactive with a hint (never a dead link). */
  disabled?: boolean;
  disabledHint?: string;
  badge?: number;
}

export function NavEntry({ item, variant }: { item: NavItem; variant: "sidebar" | "drawer" }) {
  const { Link } = useUI();
  const Icon = item.icon;
  const base =
    variant === "sidebar"
      ? "group relative flex min-h-11 items-center gap-3 rounded-md px-3 text-[0.9375rem]"
      : "flex min-h-12 items-center gap-3 rounded-md px-3 text-base";
  if (item.disabled) {
    return (
      <span aria-disabled="true" className={cn(base, variant === "sidebar" ? "cursor-not-allowed text-mist/80" : "cursor-not-allowed text-ink-2")}>
        <Icon aria-hidden className="size-5" />
        <span className="flex-1">{item.label}</span>
        {item.disabledHint ? (
          <span className={cn("rounded-sm px-1.5 text-[0.6875rem] font-semibold", variant === "sidebar" ? "bg-white/10 text-mist" : "bg-surface-2 text-ink-2")}>
            {item.disabledHint}
          </span>
        ) : null}
      </span>
    );
  }
  return (
    <Link
      href={item.href}
      aria-current={item.active ? "page" : undefined}
      className={cn(
        base,
        variant === "sidebar" && (item.active ? "bg-white/12 font-semibold text-cream" : "text-cream/90 hover:bg-white/8 hover:text-cream"),
        variant === "drawer" && (item.active ? "bg-surface-2 font-semibold text-ink" : "text-ink hover:bg-surface-2"),
      )}
    >
      {item.active && variant === "sidebar" ? <span aria-hidden className="absolute inset-y-2 start-0 w-1 rounded-full bg-lime" /> : null}
      <Icon aria-hidden className="size-5" />
      <span className="flex-1">{item.label}</span>
      {item.badge ? <span className="rounded-full bg-lime px-2 text-xs font-bold text-navy">{item.badge}</span> : null}
    </Link>
  );
}

export function Sidebar({ logo, items, footer }: { logo: ReactNode; items: NavItem[]; footer?: ReactNode }) {
  const { labels } = useUI();
  return (
    <aside className="hidden w-[var(--shell-sidebar)] shrink-0 self-stretch bg-navy text-cream md:block" data-testid="sidebar">
      <div className="sticky top-0 flex h-dvh flex-col">
      <div className="flex h-20 items-center px-5">{logo}</div>
      <nav aria-label={labels.mainNav} className="flex-1 overflow-y-auto px-3 py-2">
        <ul className="space-y-1">
          {items.map((it) => (
            <li key={it.key}>
              <NavEntry item={it} variant="sidebar" />
            </li>
          ))}
        </ul>
      </nav>
      {footer ? <div className="border-t border-white/10 px-5 py-4 text-xs text-mist">{footer}</div> : null}
      </div>
    </aside>
  );
}

export function TopBar({
  title,
  breadcrumbs,
  mobileLogo,
  actions,
}: {
  title: ReactNode;
  breadcrumbs?: { label: ReactNode; href?: string }[];
  mobileLogo?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface-1/95 backdrop-blur" data-testid="topbar">
      <div className="flex min-h-16 items-center gap-3 px-4 md:px-8">
        {mobileLogo ? <div className="md:hidden">{mobileLogo}</div> : null}
        <div className="min-w-0 flex-1">
          {/* §10.2: with a parent crumb, the breadcrumb is the title line (title not repeated). */}
          {breadcrumbs && breadcrumbs.length > 1 ? (
            <>
              <div className="hidden md:block [&_li:last-child_span]:text-lg [&_li:last-child_span]:font-semibold">
                <Breadcrumbs items={breadcrumbs} />
              </div>
              <p className="truncate text-base font-semibold text-ink md:hidden" aria-hidden="true">
                {title}
              </p>
            </>
          ) : (
            <p className="truncate text-base font-semibold text-ink md:text-lg" aria-hidden="true">
              {title}
            </p>
          )}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-1">{actions}</div> : null}
      </div>
    </header>
  );
}

/** ContextStrip: always-visible person, couple status and consent status (docs/09 §3). */
/** ContextStrip (§10.3): compact chips. `label` is announced to screen readers only; pass a ContextChip as `value`. */
export function ContextStrip({ items, label }: { items: { key: string; label?: string; value: ReactNode }[]; label: string }) {
  return (
    <section aria-label={label} className="border-b border-line bg-surface-2" data-testid="context-strip">
      <ul className="flex flex-wrap items-center gap-2 px-4 py-2 md:px-8">
        {items.map((it) => (
          <li key={it.key} className="flex shrink-0 items-center">
            {it.label ? <span className="sr-only">{it.label}: </span> : null}
            {it.value}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ShellFooter({ compliance, environment }: { compliance: ReactNode; environment?: ReactNode }) {
  return (
    <footer className="border-t border-line bg-surface-1 px-4 py-4 text-sm md:px-8" data-testid="shell-footer">
      <div className="mx-auto flex max-w-[var(--content-max)] flex-col gap-1 md:flex-row md:items-center md:justify-between">
        <p className="font-medium text-ink" data-testid="compliance-line">
          {compliance}
        </p>
        {environment ? <p className="text-ink-2">{environment}</p> : null}
      </div>
    </footer>
  );
}

/** AppShell: composes the regions. Children render inside <main id="main">. */
export function AppShell({
  environment,
  sidebar,
  topBar,
  contextStrip,
  bottomTabs,
  footer,
  children,
  theme = "clinic",
}: {
  environment?: ReactNode;
  sidebar: ReactNode;
  topBar: ReactNode;
  contextStrip?: ReactNode;
  bottomTabs?: ReactNode;
  footer: ReactNode;
  children: ReactNode;
  theme?: "clinic" | "ledger";
}) {
  const { labels } = useUI();
  return (
    <div data-theme={theme} className="min-h-dvh bg-surface-0 text-ink">
      <a
        href="#main"
        className="sr-only z-[70] focus:not-sr-only focus:fixed focus:start-3 focus:top-3 focus:rounded-md focus:bg-lime focus:px-4 focus:py-2 focus:font-semibold focus:text-navy"
      >
        {labels.skipToContent}
      </a>
      {environment}
      <div className="flex">
        {sidebar}
        <div className="flex min-h-dvh min-w-0 flex-1 flex-col">
          {topBar}
          {contextStrip}
          <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[var(--content-max)] flex-1 px-4 py-6 outline-none md:px-8 md:py-8">
            {children}
          </main>
          <div className="pb-16 md:pb-0">{footer}</div>
        </div>
      </div>
      {bottomTabs}
    </div>
  );
}

/** PageHeader: page title (h1) + description + the one per-surface SIMULATED badge + actions. */
export function PageHeader({ title, description, badge, actions }: { title: ReactNode; description?: ReactNode; badge?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-4 md:mb-8">
      <div className="min-w-0 space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-[1.875rem] font-medium leading-tight text-ink md:text-[2.25rem]">{title}</h1>
          {badge}
        </div>
        {description ? <p className="max-w-[72ch] text-base text-ink-2">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
