// Assumptions disclosure: the pack's response-model assumptions, verbatim (DECISIONS #43).
import { useTranslations } from "next-intl";
import { evidence } from "@/lib/evidence";

export function Assumptions() {
  const t = useTranslations("assumptions");
  return (
    <details className="rounded-lg border border-line bg-surface-1 p-4" data-testid="assumptions">
      <summary className="min-h-11 cursor-pointer py-2 font-semibold text-ink">{t("show")}</summary>
      <pre tabIndex={0} role="region" aria-label={t("title")} className="mt-3 overflow-x-auto font-mono text-sm leading-relaxed text-ink" dir="ltr">
        {JSON.stringify(evidence.persona_runs.model_assumptions, null, 2)}
      </pre>
    </details>
  );
}
