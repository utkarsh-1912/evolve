"use client";
// Form controls with label, help and error, wired for a11y (aria-describedby / aria-invalid).
import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { Check } from "lucide-react";
import { useId, type ReactNode } from "react";

/** Checkbox with inline label (own label; do not wrap in FormField). */
export function Checkbox({
  label,
  help,
  checked,
  defaultChecked,
  onCheckedChange,
  disabled,
  error,
}: {
  label: ReactNode;
  help?: ReactNode;
  checked?: boolean;
  defaultChecked?: boolean;
  onCheckedChange?: (c: boolean) => void;
  disabled?: boolean;
  error?: ReactNode;
}) {
  const id = useId();
  return (
    <div className="grid gap-1">
      <div className="flex min-h-11 items-center gap-3">
        <CheckboxPrimitive.Root
          id={id}
          checked={checked}
          defaultChecked={defaultChecked}
          onCheckedChange={(c) => onCheckedChange?.(c === true)}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={help ? `${id}-help` : undefined}
          className="grid size-6 shrink-0 place-items-center rounded-sm border-2 border-neutral-500 bg-surface-1 data-[state=checked]:border-navy data-[state=checked]:bg-navy disabled:opacity-50 aria-[invalid=true]:border-escalated-ink"
        >
          <CheckboxPrimitive.Indicator>
            <Check aria-hidden className="size-4 text-cream" strokeWidth={3} />
          </CheckboxPrimitive.Indicator>
        </CheckboxPrimitive.Root>
        <label htmlFor={id} className="cursor-pointer text-ink">
          {label}
        </label>
      </div>
      {help ? (
        <p id={`${id}-help`} className="ps-9 text-sm text-ink-2">
          {help}
        </p>
      ) : null}
      {error ? <p className="ps-9 text-sm font-medium text-escalated-ink">{error}</p> : null}
    </div>
  );
}
