"use client";
// Overlays on Radix: Dialog, ConfirmDialog (A6), Drawer, Tooltip, DropdownMenu, Popover.
import * as DropdownPrimitive from "@radix-ui/react-dropdown-menu";

import { type ReactNode } from "react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";

export interface MenuItem {
  label: ReactNode;
  onSelect?: () => void;
  href?: string;
  icon?: ReactNode;
  danger?: boolean;
  disabled?: boolean;
}

/** DropdownMenu: actions menu; items may be links (rendered via the provider Link). */
export function DropdownMenu({
  trigger,
  items,
  header,
  align = "end",
}: {
  trigger: ReactNode;
  items: (MenuItem | "separator")[];
  header?: ReactNode;
  align?: "start" | "end";
}) {
  const { Link, dir } = useUI();
  const itemCls =
    "flex min-h-11 cursor-pointer select-none items-center gap-2.5 rounded-sm px-3 text-sm outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-surface-2 [&_svg]:size-4";
  return (
    <DropdownPrimitive.Root dir={dir}>
      <DropdownPrimitive.Trigger asChild>{trigger}</DropdownPrimitive.Trigger>
      <DropdownPrimitive.Portal>
        <DropdownPrimitive.Content
          align={align}
          sideOffset={6}
          className="z-50 min-w-56 rounded-md border border-line bg-surface-3 p-1 text-ink shadow-e3"
        >
          {header ? <div className="px-3 py-2 text-sm">{header}</div> : null}
          {header ? <DropdownPrimitive.Separator className="my-1 h-px bg-line" /> : null}
          {items.map((it, i) =>
            it === "separator" ? (
              <DropdownPrimitive.Separator key={i} className="my-1 h-px bg-line" />
            ) : it.href ? (
              <DropdownPrimitive.Item key={i} asChild disabled={it.disabled}>
                <Link href={it.href} className={cn(itemCls, it.danger && "text-escalated-ink")}>
                  {it.icon}
                  {it.label}
                </Link>
              </DropdownPrimitive.Item>
            ) : (
              <DropdownPrimitive.Item
                key={i}
                disabled={it.disabled}
                onSelect={it.onSelect}
                className={cn(itemCls, it.danger && "text-escalated-ink")}
              >
                {it.icon}
                {it.label}
              </DropdownPrimitive.Item>
            ),
          )}
        </DropdownPrimitive.Content>
      </DropdownPrimitive.Portal>
    </DropdownPrimitive.Root>
  );
}
