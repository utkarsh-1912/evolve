"use client";
// Counselor-only AI draft summary (api.md v1.3.0, DECISIONS #62). Clearly labelled, review before use, never shown to
// the patient, never stored on the case. If the gate blocks it, show the violations and no text. On 503 the panel
// says "unavailable" and the rest of the case keeps working. Hidden when /api/config says ai_draft_enabled=false.
import { Alert, Button, Card, CardHeader, StatusChip } from "@evolve/ui";
import { IconAction } from "@evolve/ui/shell/hints";
import { Bot, NotebookPen, ShieldAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { useConfig, useSummaryDraft } from "@/lib/queries";
import { ApiError } from "@/lib/types";
import { useFormatTs } from "../format";

export function AiDraftPanel({ caseId, onCopyToNotes, readOnly }: { caseId: string; onCopyToNotes: (text: string) => void; readOnly: boolean }) {
  const t = useTranslations("aiDraft");
  const formatTs = useFormatTs();
  const config = useConfig();
  const draft = useSummaryDraft();
  if (!config.data?.ai_draft_enabled) return null; // hidden while loading, on config error, or when disabled

  const d = draft.data;
  const providerName = (p: string) => (p === "sarvam" ? t("providerSarvam") : p === "offline-stub" ? t("providerStub") : p);
  const unavailable = draft.error instanceof ApiError && draft.error.status === 503;

  return (
    <Card className="xl:col-span-2" data-testid="ai-draft">
      <CardHeader
        title={t("title")}
        level={2}
        description={t("intro")}
        actions={
          <Button size="sm" variant="secondary" leadingIcon={<Bot aria-hidden />} loading={draft.isPending} onClick={() => draft.mutate(caseId)} data-testid="ai-draft-generate">
            {d || draft.error ? t("regenerate") : t("generate")}
          </Button>
        }
      />
      {unavailable ? (
        <Alert tone="warning" title={t("unavailable")} testId="ai-draft-unavailable">
          {t("unavailableBody")}
        </Alert>
      ) : draft.error ? (
        <Alert tone="danger" title={t("error")} testId="ai-draft-error" />
      ) : d ? (
        <section aria-labelledby="ai-draft-label" className="space-y-3 rounded-lg border border-dashed border-line-strong p-4" data-testid="ai-draft-result" data-provider={d.provider}>
          {/* Label is always visible text (never tooltip-only). */}
          <p id="ai-draft-label" className="font-semibold text-ink" data-testid="ai-draft-label">
            {t("label", { provider: providerName(d.provider) })}
          </p>
          <p className="text-xs text-ink-2" data-testid="ai-draft-meta">
            {t("meta", { provider: providerName(d.provider), model: d.model })} · <time dateTime={d.generated_at}>{formatTs(d.generated_at)}</time>
          </p>
          {d.gate.passed && d.draft ? (
            <>
              <div className="flex items-start gap-2">
                <p className="max-w-[72ch] flex-1 whitespace-pre-wrap text-ink" data-testid="ai-draft-text">
                  {d.draft}
                </p>
                {readOnly ? null : (
                  <IconAction label={t("copyToNotes")} icon={NotebookPen} variant="secondary" onClick={() => onCopyToNotes(d.draft!)} data-testid="ai-draft-copy" />
                )}
              </div>
              <p className="text-xs text-ink-2">{t("inputs", { fields: d.input_fields.join(", ") })}</p>
            </>
          ) : (
            <Alert tone="warning" icon={ShieldAlert} title={t("blocked")} testId="ai-draft-blocked">
              <ul className="list-disc ps-5">
                {d.gate.violations.map((v, i) => (
                  <li key={i}>
                    <StatusChip status="review" size="sm">
                      <span className="font-mono">{v.rule}</span>
                    </StatusChip>{" "}
                    {v.detail}
                  </li>
                ))}
              </ul>
            </Alert>
          )}
        </section>
      ) : null}
    </Card>
  );
}
