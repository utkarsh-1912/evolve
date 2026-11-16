"use client";
// Form controls with label, help and error, wired for a11y (aria-describedby / aria-invalid).
import * as SwitchPrimitive from "@radix-ui/react-switch";

import { forwardRef, useId, type ReactNode } from "react";

/** Switch (Radix) with visible label; thumb moves with logical direction (RTL-safe). */
export const Switch = forwardRef<
  HTMLButtonElement,
  {
    label?: ReactNode;
    help?: ReactNode;
    checked?: boolean;
    defaultChecked?: boolean;
    onCheckedChange?: (c: boolean) => void;
    disabled?: boolean;
    id?: string;
    "aria-label"?: string;
    "data-testid"?: string;
  }
>(function Switch({ label, help, id: idProp, ...props }, ref) {
  const autoId = useId();
  const id = idProp ?? autoId;
  const sw = (
    <SwitchPrimitive.Root
      ref={ref}
      id={id}
      aria-describedby={help ? `${id}-help` : undefined}
      className="group relative inline-flex h-8 w-14 shrink-0 cursor-pointer items-center rounded-full border-2 border-neutral-500 bg-surface-2 transition-colors duration-[var(--motion-base)] data-[state=checked]:border-navy data-[state=checked]:bg-navy disabled:cursor-not-allowed disabled:opacity-50 before:absolute before:-inset-1.5 before:content-['']"
      {...props}
    >
      <SwitchPrimitive.Thumb className="block size-6 translate-x-0.5 rounded-full bg-surface-1 shadow-e1 transition-transform duration-[var(--motion-base)] data-[state=checked]:translate-x-[26px] data-[state=checked]:bg-lime rtl:-translate-x-0.5 rtl:data-[state=checked]:-translate-x-[26px]" />
    </SwitchPrimitive.Root>
  );
  if (!label) return sw;
  return (
    <div className="flex items-start gap-3">
      <div className="flex min-h-11 items-center">{sw}</div>
      <div className="pt-2">
        <label htmlFor={id} className="cursor-pointer font-semibold text-ink">
          {label}
        </label>
        {help ? (
          <p id={`${id}-help`} className="text-sm text-ink-2">
            {help}
          </p>
        ) : null}
      </div>
    </div>
  );
});
