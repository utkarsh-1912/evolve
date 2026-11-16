"use client";
// Locked-number family: LockedNumber (+ provenance), SourceCaption, DetectionBar, IconArray.
// The ONLY way a risk number reaches the screen (P-01). No arithmetic on probabilities (P-02);
// formatLocked() is the single central formatter allowed by DECISIONS #29.
import { ChevronDown, Fingerprint } from "lucide-react";
import { useId, useState, type ReactNode } from "react";
import type { LockedField, RiskOutput } from "../contracts";
import { cn } from "../lib/cn";
import { useUI } from "../provider";

const INPUT_FIELDS = ["F", "prior_carrier_b", "detection_rate", "posterior_carrier_b", "offspring_risk"] as const;

/** Central formatter for locked values (DECISIONS #29). Strings pass through verbatim. */
export function formatLocked(value: string | number, format: "raw" | "percent", locale: string): string {
  if (typeof value === "string") return value;
  if (format === "percent") {
    return new Intl.NumberFormat(locale === "ar" ? "ar-AE-u-nu-latn" : "en", { style: "percent", maximumFractionDigits: 1 }).format(value);
  }
  return String(value);
}

export function LockedNumber({
  record,
  field,
  size = "inline",
  format = "raw",
  label,
  provenance = true,
  className,
}: {
  record: RiskOutput;
  field: LockedField;
  size?: "inline" | "large" | "giant";
  format?: "raw" | "percent";
  label?: ReactNode;
  provenance?: boolean;
  className?: string;
}) {
  const { labels, locale } = useUI();
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const value = record[field];

  let body: ReactNode;
  if (value === null || value === undefined) {
    body = (
      <span className="text-base font-normal text-ink-2" data-locked-missing="true">
        {labels.notComputed} <span className="text-sm">({labels.notComputedHelp})</span>
      </span>
    );
  } else {
    const text = formatLocked(value, format, locale);
    const m = size !== "inline" ? /^(1 in)\s+(.+)$/.exec(text) : null;
    body = m ? (
      <>
        <span className="align-baseline text-[0.38em] font-normal">{m[1]}</span>{" "}
        <span>{m[2]}</span>
      </>
    ) : (
      text
    );
  }

  const sizeCls =
    size === "giant"
      ? "font-display text-[clamp(3.5rem,12vw,6rem)] font-light leading-none tracking-tight"
      : size === "large"
        ? "font-display text-[clamp(1.875rem,5vw,2.25rem)] font-normal leading-none"
        : "font-semibold";

  return (
    <span className={cn(size === "inline" ? "inline" : "block", className)}>
      {label ? <span className="mb-2 block text-sm text-ink-2">{label}</span> : null}
      <span className={cn(sizeCls, "text-ink")} data-locked-field={field} data-locked-digest={record.digest} data-testid={`locked-${field}`} dir="ltr">
        {body}
      </span>
      {provenance ? (
        <span className={size === "inline" ? "ms-2 inline-block align-middle" : "mt-3 block"}>
          <button
            type="button"
            className="inline-flex min-h-11 items-center gap-2 rounded-md px-2 text-sm font-semibold text-navy hover:bg-surface-2 [[data-theme=ledger]_&]:text-lime"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((o) => !o)}
          >
            <Fingerprint aria-hidden className="size-4" />
            {open ? labels.hideCounted : labels.howCounted}
            <ChevronDown aria-hidden className={cn("size-4 transition-transform duration-[var(--motion-base)]", open && "rotate-180")} />
          </button>
        </span>
      ) : null}
      {provenance && open ? (
        <span id={panelId} className="mt-2 block rounded-lg border border-line bg-surface-2 p-4 text-start" data-testid="provenance">
          <span className="block text-xs font-semibold uppercase tracking-[0.06em] text-ink-2">{labels.formula}</span>
          <span className="mt-1 block font-mono text-sm text-ink" dir="ltr">
            {labels.formulas[record.scenario]}
          </span>
          <span className="mt-3 block text-xs font-semibold uppercase tracking-[0.06em] text-ink-2">{labels.inputs}</span>
          <span className="mt-1 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            {INPUT_FIELDS.filter((k) => record[k] !== null && record[k] !== undefined).map((k) => (
              <span key={k} className="contents">
                <span className="text-ink-2">{labels.inputNames[k]}</span>
                <span className="break-all font-mono text-ink" dir="ltr">
                  {String(record[k])}
                </span>
              </span>
            ))}
            <span className="text-ink-2">{labels.scenario}</span>
            <span className="font-mono text-ink" dir="ltr">
              {record.scenario}
            </span>
            <span className="text-ink-2">{labels.contract}</span>
            <span className="font-mono text-ink" dir="ltr">
              {record.contract_version}
            </span>
            <span className="text-ink-2">{labels.digest}</span>
            <span className="font-mono text-ink" dir="ltr" title={record.digest}>
              {record.digest.slice(0, 12)}…
            </span>
          </span>
          <span className="mt-3 block text-xs text-ink-2">{labels.provenanceSource}</span>
        </span>
      ) : null}
    </span>
  );
}

/** SourceCaption: mandatory under every number-bearing visual (docs/03 §5). Sans, not mono (A7). */
export function SourceCaption({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-xs leading-relaxed text-ink-2", className)}>{children}</p>;
}

/** DetectionBar: solid = detected by the test; hatched = what a negative cannot rule out. scaleX(locked d), no arithmetic. */
export function DetectionBar({ record, detectedLabel, missedLabel, title }: { record: RiskOutput; detectedLabel: string; missedLabel: string; title: string }) {
  const d = record.detection_rate;
  if (d === null || d === undefined) return null;
  return (
    <figure className="m-0 space-y-3" data-testid="detection-bar">
      <figcaption className="text-base font-semibold text-ink">{title}</figcaption>
      <div role="img" aria-label={`${detectedLabel} / ${missedLabel}`} className="hatch relative h-8 overflow-hidden rounded-md border border-review bg-review/10">
        <div className="absolute inset-y-0 start-0 w-full origin-left bg-navy rtl:origin-right" style={{ transform: `scaleX(${d})` }} />
      </div>
      <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink">
        <li className="flex items-center gap-2">
          <span aria-hidden className="inline-block h-3 w-5 rounded-sm bg-navy" />
          {detectedLabel}
        </li>
        <li className="flex items-center gap-2">
          <span aria-hidden className="hatch inline-block h-3 w-5 rounded-sm border border-review" />
          {missedLabel}
        </li>
      </ul>
    </figure>
  );
}

/** IconArray (1-in-N): N read from the locked display string; drawn only for small N. */
export function IconArray({ oneIn, caption, max = 12 }: { oneIn: string | null | undefined; caption: string; max?: number }) {
  const m = oneIn ? /^1 in ([0-9][0-9,]*)$/.exec(oneIn) : null;
  const n = m ? Number(m[1].replace(/,/g, "")) : NaN;
  if (!Number.isInteger(n) || n < 2 || n > max) return null;
  return (
    <figure className="m-0 space-y-2" data-testid="icon-array">
      <div role="img" aria-label={oneIn ?? ""} className="flex flex-wrap gap-3">
        {Array.from({ length: n }, (_, i) => {
          const hi = i === 0;
          const stroke = hi ? "var(--signal-escalated-ink)" : "var(--evolve-navy)";
          const fill = hi ? "var(--signal-escalated)" : "none";
          return (
            <svg key={i} width="36" height="48" viewBox="0 0 44 60" aria-hidden>
              <circle cx="22" cy="14" r="10" fill={fill} stroke={stroke} strokeWidth="2.5" />
              <path d="M6 58c0-12 7-22 16-22s16 10 16 22" fill={fill} stroke={stroke} strokeWidth="2.5" />
            </svg>
          );
        })}
      </div>
      <figcaption className="text-sm text-ink-2">{caption}</figcaption>
    </figure>
  );
}
