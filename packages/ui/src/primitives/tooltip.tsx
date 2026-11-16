"use client";
// Overlays on Radix: Dialog, ConfirmDialog (A6), Drawer, Tooltip, DropdownMenu, Popover.
import * as TooltipPrimitive from "@radix-ui/react-tooltip";

import { type ReactNode } from "react";

export const TooltipProvider = TooltipPrimitive.Provider;

/** Tooltip: supplementary only; never the sole carrier of essential information. */
export function Tooltip({ content, children, side = "top" }: { content: ReactNode; children: ReactNode; side?: "top" | "bottom" | "left" | "right" }) {
  return (
    <TooltipPrimitive.Root delayDuration={250}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          className="z-50 max-w-xs rounded-md bg-neutral-950 px-3 py-2 text-sm text-neutral-50 shadow-e2 [[data-theme=ledger]_&]:bg-neutral-900 [[data-theme=ledger]_&]:text-neutral-50"
        >
          {content}
          <TooltipPrimitive.Arrow className="fill-neutral-950" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
