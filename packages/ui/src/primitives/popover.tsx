"use client";
// Overlays on Radix: Dialog, ConfirmDialog (A6), Drawer, Tooltip, DropdownMenu, Popover.
import * as PopoverPrimitive from "@radix-ui/react-popover";

import { type ReactNode } from "react";

/** Popover: anchored non-modal panel (used by NotificationBell). */
export function Popover({
  trigger,
  children,
  align = "end",
  label,
}: {
  trigger: ReactNode;
  children: ReactNode;
  align?: "start" | "center" | "end";
  label: string;
}) {
  return (
    <PopoverPrimitive.Root>
      <PopoverPrimitive.Trigger asChild>{trigger}</PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align={align}
          sideOffset={8}
          aria-label={label}
          className="z-50 w-[min(92vw,24rem)] rounded-lg border border-line bg-surface-3 text-ink shadow-e3"
        >
          {children}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
