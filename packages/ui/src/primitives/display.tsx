"use client";
// Card, StatCard, Badge, StatusChip, VisibilityChip, Avatar.
import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle, CheckCircle2, Clock3, Eye, Info, Lock, Users, type LucideIcon } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "../lib/cn";
import { useUI } from "../provider";
import type { Visibility } from "../contracts";

const cardVariants = cva("rounded-xl text-ink", {
  variants: {
    variant: {
      flat: "border border-line bg-surface-1",
      raised: "bg-surface-1 shadow-e2",
      well: "bg-surface-2",
      inverse: "bg-surface-inverse text-cream",
    },
    padding: { none: "", sm: "p-4", md: "p-5 sm:p-6", lg: "p-6 sm:p-8" },
  },
  defaultVariants: { variant: "flat", padding: "md" },
});

export interface CardProps extends HTMLAttributes<HTMLElement>, VariantProps<typeof cardVariants> {
  as?: "section" | "article" | "div" | "li" | "aside";
}

export function Card({ as: Tag = "section", variant, padding, className, ...props }: CardProps) {
  return <Tag className={cn(cardVariants({ variant, padding }), className)} {...props} />;
}

export function CardHeader({
  title,
  description,
  actions,
  eyebrow,
  level = 2,
  id,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  eyebrow?: ReactNode;
  level?: 2 | 3;
  id?: string;
}) {
  const H = level === 2 ? "h2" : "h3";
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 space-y-1">
        {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-2">{eyebrow}</p> : null}
        <H id={id} className="text-lg font-semibold leading-snug text-ink">
          {title}
        </H>
        {description ? <p className="max-w-[72ch] text-sm text-ink-2">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}

/** StatCard: label + value (+ optional status chip / action). Value must be a count or LockedNumber, never a computed risk. */
export function StatCard({
  label,
  value,
  icon: Icon,
  footer,
  className,
}: {
  label: ReactNode;
  value: ReactNode;
  icon?: LucideIcon;
  footer?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("flex flex-col gap-3", className)}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-ink-2">{label}</p>
        {Icon ? (
          <span className="grid size-9 place-items-center rounded-md bg-surface-2 text-navy">
            <Icon aria-hidden className="size-5" />
          </span>
        ) : null}
      </div>
      <div className="text-2xl font-semibold text-ink">{value}</div>
      {footer ? <div className="mt-auto text-sm">{footer}</div> : null}
    </Card>
  );
}

const badgeVariants = cva("inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-semibold", {
  variants: {
    tone: {
      neutral: "bg-surface-2 text-ink",
      brand: "bg-navy text-cream",
      outline: "border border-line-strong text-ink-2",
      simulated: "border border-dashed border-navy/50 bg-surface-1 text-navy tracking-wide uppercase",
    },
  },
  defaultVariants: { tone: "neutral" },
});

/** Badge: neutral metadata (counts, tags). For meaning use StatusChip. */
export function Badge({ tone, className, ...props }: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

export type Status = "compatible" | "review" | "escalated" | "vault" | "info" | "neutral";

const STATUS: Record<Status, { cls: string; Icon: LucideIcon }> = {
  compatible: { cls: "border-compatible bg-compatible/10 text-compatible-ink", Icon: CheckCircle2 },
  review: { cls: "border-review bg-review/15 text-review-ink", Icon: Clock3 },
  escalated: { cls: "border-escalated bg-escalated/10 text-escalated-ink", Icon: AlertTriangle },
  vault: { cls: "border-vault bg-vault/10 text-vault-ink", Icon: Lock },
  info: { cls: "border-info/50 bg-info/10 text-info-ink", Icon: Info },
  neutral: { cls: "border-line-strong bg-surface-2 text-ink", Icon: Info },
};

/** StatusChip: signal color + icon + text, always together (docs/03 §3, color-blind safe). */
export function StatusChip({
  status,
  children,
  size = "md",
  className,
  icon,
}: {
  status: Status;
  children: ReactNode;
  size?: "sm" | "md" | "lg";
  className?: string;
  icon?: LucideIcon;
}) {
  const { cls, Icon: Default } = STATUS[status];
  const Icon = icon ?? Default;
  return (
    <span
      data-status={status}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-semibold",
        size === "sm" && "px-2 py-0.5 text-xs [&_svg]:size-3.5",
        size === "md" && "px-2.5 py-1 text-sm [&_svg]:size-4",
        size === "lg" && "border-2 px-4 py-1.5 text-base [&_svg]:size-5",
        cls,
        className,
      )}
    >
      <Icon aria-hidden />
      {children}
    </span>
  );
}

/** VisibilityChip: who can see this item (P-06 made visible). */
export function VisibilityChip({ visibility, className }: { visibility: Visibility; className?: string }) {
  const { labels } = useUI();
  const Icon = visibility === "only_you" ? Lock : visibility === "couple" ? Users : Eye;
  return (
    <span
      data-visibility={visibility}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full bg-vault/10 px-2.5 py-1 text-xs font-semibold text-vault-ink [&_svg]:size-3.5",
        className,
      )}
    >
      <Icon aria-hidden />
      {labels.visibility[visibility]}
    </span>
  );
}

/** Avatar: initials fallback; never a photo of a patient (synthetic only). */
export function Avatar({ name, src, size = "md" }: { name: string; src?: string; size?: "sm" | "md" | "lg" }) {
  const initials = name
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return (
    <AvatarPrimitive.Root
      className={cn(
        "inline-grid shrink-0 place-items-center overflow-hidden rounded-full bg-navy font-semibold text-cream",
        size === "sm" && "size-8 text-xs",
        size === "md" && "size-10 text-sm",
        size === "lg" && "size-14 text-base",
      )}
    >
      {src ? <AvatarPrimitive.Image src={src} alt="" className="size-full object-cover" /> : null}
      <AvatarPrimitive.Fallback aria-hidden>{initials}</AvatarPrimitive.Fallback>
      <span className="sr-only">{name}</span>
    </AvatarPrimitive.Root>
  );
}
