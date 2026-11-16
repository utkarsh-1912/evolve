"use client";
// Role-based app shell (docs/09 §3): Sidebar (264px) + TopBar + ContextStrip + main + ShellFooter;
// mobile (<768px): TopBar + BottomTabs (+ "More" drawer). Logical properties throughout (RTL-safe).

import { type ReactNode } from "react";

import { fmt, useUI } from "../provider";
import { Avatar } from "../primitives/display";

import { DropdownMenu, type MenuItem } from "../primitives/dropdown";

export function ProfileMenu({ name, detail, items }: { name: string; detail?: ReactNode; items: (MenuItem | "separator")[] }) {
  const { labels } = useUI();
  return (
    <DropdownMenu
      header={
        <div>
          <p className="font-semibold text-ink">{fmt(labels.signedInAs, { name })}</p>
          {detail ? <p className="text-xs text-ink-2">{detail}</p> : null}
        </div>
      }
      items={items}
      trigger={
        <button type="button" aria-label={`${labels.profile}: ${name}`} className="grid size-11 place-items-center rounded-full hover:bg-surface-2" data-testid="profile-menu">
          <Avatar name={name} size="sm" />
        </button>
      }
    />
  );
}
