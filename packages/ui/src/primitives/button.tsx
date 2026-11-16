"use client";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { ChevronRight, Loader2 } from "lucide-react";
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";

export const buttonVariants = cva(
  "relative inline-flex select-none items-center justify-center gap-2 whitespace-nowrap font-semibold transition-[background-color,border-color,color,box-shadow] duration-[var(--motion-fast)] ease-[var(--ease-standard)] disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-navy text-cream hover:bg-navy-2 shadow-e1",
        secondary: "border border-line-strong bg-surface-1 text-ink hover:border-navy hover:bg-surface-2",
        ghost: "text-ink hover:bg-surface-2",
        danger: "bg-escalated-ink text-white hover:brightness-110 shadow-e1 [[data-theme=ledger]_&]:text-[#141412]",
        "danger-outline": "border-2 border-escalated-ink bg-transparent text-escalated-ink hover:bg-escalated/10",
        lime: "bg-lime text-[var(--evolve-navy)] hover:brightness-95 [[data-theme=ledger]_&]:text-[#141412]",
        link: "h-auto min-h-0 px-0 text-navy underline underline-offset-4 hover:no-underline",
      },
      size: {
        sm: "min-h-11 rounded-md px-3 text-sm [&_svg]:size-4",
        md: "min-h-11 rounded-md px-4 text-[0.9375rem] [&_svg]:size-[18px]",
        lg: "min-h-12 rounded-lg px-6 text-base [&_svg]:size-5",
      },
      block: { true: "w-full", false: "" },
    },
    defaultVariants: { variant: "primary", size: "md", block: false },
  },
);

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
}

/** Button: primary / secondary / ghost / danger; sm / md / lg; loading. Every size keeps a 44px target (docs/09 §7). */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, block, asChild, loading, leadingIcon, trailingIcon, children, disabled, ...props },
  ref,
) {
  const { labels } = useUI();
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      ref={ref}
      className={cn(buttonVariants({ variant, size, block }), className)}
      disabled={asChild ? undefined : disabled || loading}
      aria-busy={loading || undefined}
      {...(asChild ? {} : { type: props.type ?? "button" })}
      {...props}
    >
      {asChild ? (
        children
      ) : (
        <>
          {loading ? <Loader2 aria-hidden className="animate-spin" /> : leadingIcon}
          <span>{children}</span>
          {loading ? <span className="sr-only">{labels.loading}</span> : trailingIcon}
        </>
      )}
    </Comp>
  );
});

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Accessible name (required: icon-only). */
  label: string;
  variant?: "ghost" | "secondary" | "primary" | "inverse";
  size?: "md" | "lg";
  children: ReactNode;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, variant = "ghost", size = "md", className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      aria-label={label}
      title={label}
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center rounded-md transition-colors duration-[var(--motion-fast)] disabled:opacity-50 [&_svg]:size-5",
        size === "md" ? "size-11" : "size-12",
        variant === "ghost" && "text-ink hover:bg-surface-2",
        variant === "secondary" && "border border-line-strong bg-surface-1 text-ink hover:border-navy",
        variant === "primary" && "bg-navy text-cream hover:bg-navy-2",
        variant === "inverse" && "text-cream hover:bg-white/10",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
});

/** ChamferCTA: marketing pages only (docs/09 §5). At most one per screen. */
export function ChamferCTA({ href, children, className }: { href: string; children: ReactNode; className?: string }) {
  const { Link } = useUI();
  return (
    <Link
      href={href}
      className={cn(
        "chamfer inline-flex min-h-12 items-center gap-3 bg-lime px-8 py-3 text-sm font-bold uppercase tracking-[0.12em] text-[var(--evolve-navy)] transition-[filter] hover:brightness-95 [[data-theme=ledger]_&]:text-[#141412]",
        className,
      )}
    >
      {children}
      <ChevronRight aria-hidden className="size-4 rtl:-scale-x-100" />
    </Link>
  );
}
