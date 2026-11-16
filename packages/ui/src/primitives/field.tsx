"use client";
// Form controls with label, help and error, wired for a11y (aria-describedby / aria-invalid).
import { AlertCircle } from "lucide-react";
import { cloneElement, createContext, forwardRef, isValidElement, useContext, useId, type InputHTMLAttributes, type ReactElement, type ReactNode, type TextareaHTMLAttributes } from "react";
import { cn } from "../lib/cn";

export const control =
  "w-full rounded-md border bg-surface-1 px-3 text-ink placeholder:text-ink-2 transition-colors duration-[var(--motion-fast)] hover:border-neutral-400 disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-ink-2 aria-[invalid=true]:border-escalated-ink";

interface FieldCtx {
  id: string;
  describedBy?: string;
  invalid: boolean;
}
const FieldContext = createContext<FieldCtx | null>(null);
export const useField = () => useContext(FieldContext);

/** FormField: label + control + help + error. Passes id/aria to its single child control. */
export function FormField({
  label,
  help,
  error,
  required,
  children,
  className,
  hideLabel,
}: {
  label: ReactNode;
  help?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  hideLabel?: boolean;
  children: ReactElement;
  className?: string;
}) {
  const id = useId();
  const helpId = help ? `${id}-help` : undefined;
  const errId = error ? `${id}-err` : undefined;
  const describedBy = [helpId, errId].filter(Boolean).join(" ") || undefined;
  return (
    <FieldContext.Provider value={{ id, describedBy, invalid: !!error }}>
      <div className={cn("grid gap-1.5", className)}>
        <label htmlFor={id} className={cn("text-sm font-semibold text-ink", hideLabel && "sr-only")}>
          {label}
          {required ? <span aria-hidden className="ms-0.5 text-escalated-ink">*</span> : null}
        </label>
        {isValidElement(children)
          ? cloneElement(children as ReactElement<Record<string, unknown>>, {
              id,
              "aria-describedby": describedBy,
              "aria-invalid": error ? true : undefined,
              "aria-required": required || undefined,
            })
          : children}
        {help ? (
          <p id={helpId} className="text-sm text-ink-2">
            {help}
          </p>
        ) : null}
        {error ? (
          <p id={errId} className="flex items-center gap-1.5 text-sm font-medium text-escalated-ink">
            <AlertCircle aria-hidden className="size-4" />
            {error}
          </p>
        ) : null}
      </div>
    </FieldContext.Provider>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...props },
  ref,
) {
  return <input ref={ref} className={cn(control, "min-h-11", className)} {...props} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(
  { className, rows = 4, ...props },
  ref,
) {
  return <textarea ref={ref} rows={rows} className={cn(control, "min-h-24 py-2.5 leading-normal", className)} {...props} />;
});
