"use client";
// Form controls with label, help and error, wired for a11y (aria-describedby / aria-invalid).
import * as RadioGroupPrimitive from "@radix-ui/react-radio-group";

import { useId, type ReactNode } from "react";
import { cn } from "../lib/cn";

/** RadioGroup: no default selection unless the caller provides one (non-directive, P-13). */
export function RadioGroup({
  legend,
  options,
  value,
  onValueChange,
  disabled,
  orientation = "vertical",
}: {
  legend: ReactNode;
  options: { value: string; label: ReactNode; help?: ReactNode }[];
  value?: string;
  onValueChange?: (v: string) => void;
  disabled?: boolean;
  orientation?: "vertical" | "horizontal";
}) {
  const id = useId();
  return (
    <fieldset className="grid gap-2">
      <legend className="mb-1 text-sm font-semibold text-ink">{legend}</legend>
      <RadioGroupPrimitive.Root
        value={value}
        onValueChange={onValueChange}
        disabled={disabled}
        orientation={orientation}
        className={cn("grid gap-1", orientation === "horizontal" && "flex flex-wrap gap-4")}
      >
        {options.map((o, i) => (
          <div key={o.value} className="flex min-h-11 items-start gap-3 py-1">
            <RadioGroupPrimitive.Item
              id={`${id}-${i}`}
              value={o.value}
              className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border-2 border-neutral-500 bg-surface-1 data-[state=checked]:border-navy disabled:opacity-50"
            >
              <RadioGroupPrimitive.Indicator className="size-3 rounded-full bg-navy" />
            </RadioGroupPrimitive.Item>
            <label htmlFor={`${id}-${i}`} className="cursor-pointer">
              <span className="block text-ink">{o.label}</span>
              {o.help ? <span className="block text-sm text-ink-2">{o.help}</span> : null}
            </label>
          </div>
        ))}
      </RadioGroupPrimitive.Root>
    </fieldset>
  );
}
