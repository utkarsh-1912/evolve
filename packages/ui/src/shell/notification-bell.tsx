"use client";
// Role-based app shell (docs/09 §3): Sidebar (264px) + TopBar + ContextStrip + main + ShellFooter;
// mobile (<768px): TopBar + BottomTabs (+ "More" drawer). Logical properties throughout (RTL-safe).
import { Bell } from "lucide-react";
import { type ReactNode } from "react";
import { cn } from "../lib/cn";
import { fmt, useUI } from "../provider";

import { Button, IconButton } from "../primitives/button";
import { Popover } from "../primitives/popover";

export interface NotificationItem {
  id: string;
  title: ReactNode;
  ts: string;
  href: string;
  read: boolean;
}

export function NotificationBell({
  items,
  onMarkAllRead,
  formatTs,
  loading,
  footer,
}: {
  items: NotificationItem[];
  onMarkAllRead?: () => void;
  formatTs?: (iso: string) => string;
  loading?: boolean;
  /** Optional link row, e.g. "View all notifications". */
  footer?: ReactNode;
}) {
  const { labels, Link } = useUI();
  const unread = items.filter((i) => !i.read).length;
  const name = unread ? `${labels.notifications}, ${fmt(labels.notificationsUnread, { count: unread })}` : labels.notifications;
  return (
    <Popover
      label={labels.notifications}
      trigger={
        <IconButton label={name} data-testid="notification-bell">
          <Bell aria-hidden />
          {unread ? (
            <span aria-hidden className="absolute end-1.5 top-1.5 grid min-w-5 place-items-center rounded-full bg-escalated-ink px-1 text-[0.6875rem] font-bold text-white">
              {unread}
            </span>
          ) : null}
        </IconButton>
      }
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <p className="font-semibold">{labels.notifications}</p>
        {unread && onMarkAllRead ? (
          <Button variant="ghost" size="sm" onClick={onMarkAllRead}>
            {labels.markAllRead}
          </Button>
        ) : null}
      </div>
      {loading ? (
        <p className="px-4 py-6 text-sm text-ink-2">{labels.loading}…</p>
      ) : items.length === 0 ? (
        <p className="px-4 py-6 text-sm text-ink-2">{labels.noNotifications}</p>
      ) : (
        <ul className="max-h-80 overflow-y-auto py-1">
          {items.map((n) => (
            <li key={n.id}>
              <Link href={n.href} className="flex min-h-12 gap-3 px-4 py-2.5 hover:bg-surface-2">
                <span aria-hidden className={cn("mt-1.5 size-2 shrink-0 rounded-full", n.read ? "bg-transparent" : "bg-navy")} />
                <span className="min-w-0 flex-1">
                  <span className={cn("block text-sm", n.read ? "text-ink-2" : "font-semibold text-ink")}>{n.title}</span>
                  <time dateTime={n.ts} className="block text-xs text-ink-2">
                    {formatTs ? formatTs(n.ts) : n.ts}
                  </time>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {footer ? <div className="border-t border-line px-4 py-2">{footer}</div> : null}
    </Popover>
  );
}
