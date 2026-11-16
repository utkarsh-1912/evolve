// Shared dashboard building blocks (Ledger patterns, docs/03 §5): section frame with micro-label,
// metric row (value + CI + k/n), target/verdict chip. Values come from the evidence pack only.
import { StatusChip } from "@evolve/ui";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import type { Share } from "@/lib/evidence";
import { count, pct } from "@/lib/format";
import { cn } from "@evolve/ui";

export function Section({
  id,
  label,
  title,
  description,
  children,
  className,
}: {
  id: string;
  label: string;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className={cn("scroll-mt-24 border-t border-line py-10", className)}>
      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-3">
          <p className="font-mono text-xs uppercase tracking-[0.12em] text-ink-2">{label}</p>
        </div>
        <div className="space-y-3 lg:col-span-9">
          <h2 id={`${id}-h`} className="font-display text-3xl font-semibold leading-tight tracking-tight text-ink">
            {title}
          </h2>
          {description ? <p className="max-w-[72ch] text-base text-ink-2">{description}</p> : null}
        </div>
      </div>
      <div className="mt-8">{children}</div>
    </section>
  );
}

/** One measured share: big value, 95% CI and k/n underneath. */
export function ShareValue({ share, size = "lg", testId }: { share: Share; size?: "lg" | "md"; testId?: string }) {
  const locale = useLocale();
  const t = useTranslations("dim");
  return (
    <div data-testid={testId}>
      <p
        className={cn(
          "font-display font-light leading-none tracking-tight text-ink",
          size === "lg" ? "text-5xl xl:text-6xl" : "text-3xl",
        )}
        dir="ltr"
      >
        {pct(share.value, locale)}
      </p>
      <p className="mt-2 font-mono text-sm text-ink-2" dir="ltr">
        {t("ci", { lo: pct(share.ci95[0], locale), hi: pct(share.ci95[1], locale) })} · {t("kn", { k: count(share.k, locale), n: count(share.n, locale) })}
      </p>
    </div>
  );
}

/** The pack's own verdict for a dimension (never re-computed here). */
export function Verdict({ meets, testId }: { meets: boolean; testId?: string }) {
  const t = useTranslations("dim");
  return (
    <span data-testid={testId} data-meets={meets}>
      <StatusChip status={meets ? "compatible" : "escalated"}>{meets ? t("met") : t("notMet")}</StatusChip>
    </span>
  );
}

export function KV({ k, v, mono }: { k: ReactNode; v: ReactNode; mono?: boolean }) {
  return (
    <dl className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-t border-line py-2 first:border-t-0">
      <dt className="text-sm text-ink-2">{k}</dt>
      <dd className={cn("text-sm font-semibold text-ink", mono && "font-mono")}>{v}</dd>
    </dl>
  );
}
