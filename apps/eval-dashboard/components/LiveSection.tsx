"use client";
// Live guardrail terminal (docs/03 §5 "terminal panel") + Gate probe (DECISIONS #38).
// Feed: GET /api/guardrail/events every 2 s (no message text, no genes). Probe: POST /api/demo/gate-probe, which
// runs the draft through BioethicsSupervisor ONLY and never delivers anything. No mock: if the backend is down the
// UI says so. The pack lines at the top of the terminal are read from the evidence pack.
import { Button, Card, FormField, GuardBanner, Select, StatusChip, Textarea } from "@evolve/ui";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE, ApiError, getGuardrailEvents, postGateProbe, RECIPIENTS, type GateResult, type GuardrailEvent } from "@/lib/api";
import { evidence } from "@/lib/evidence";

const GLYPH: Record<GuardrailEvent["outcome"], string> = { passed: "✔", blocked: "✖", rewritten: "↻", escalated: "⚑" };
const TONE: Record<GuardrailEvent["outcome"], string> = {
  passed: "text-compatible-ink",
  blocked: "text-escalated-ink",
  rewritten: "text-review-ink",
  escalated: "text-review-ink",
};
const SHOW = 200;

function PackLines() {
  const t = useTranslations("terminal");
  const feed = evidence.guardrail_feed.by_rule.all;
  return (
    <>
      <li className="text-ink-2"># {t("pack")} · {evidence.build.utc}</li>
      {Object.entries(evidence.tests).map(([suite, s]) => (
        <li key={suite} className={s.failed + s.errors > 0 ? "text-escalated-ink" : "text-compatible-ink"}>
          {s.failed + s.errors > 0 ? "✖ " : "✔ "}
          {s.failed + s.errors > 0
            ? t("packFailed", { suite, failed: s.failed + s.errors, tests: s.tests })
            : t("packTests", { suite, passed: s.passed, tests: s.tests })}
        </li>
      ))}
      <li className={evidence.guardrail_check.ok ? "text-compatible-ink" : "text-escalated-ink"}>
        {evidence.guardrail_check.ok ? "✔ " : "✖ "}
        {t("packGuard", { status: evidence.guardrail_check.ok ? "OK" : "FAIL" })}
      </li>
      {feed ? (
        <li className="text-ink-2">
          · {t("packFeed", { passed: feed.passed, blocked: feed.blocked, rewritten: feed.rewritten, escalated: feed.escalated })}
        </li>
      ) : null}
    </>
  );
}

export function LiveSection() {
  const t = useTranslations("terminal");
  const tp = useTranslations("probe");
  const locale = useLocale();
  const events = useQuery({ queryKey: ["guardrail-events"], queryFn: getGuardrailEvents, refetchInterval: 2000, retry: false });
  const list = useMemo(() => events.data ?? [], [events.data]);
  const probeCount = list.filter((e) => e.message_id === "probe").length;

  // Probe state: which probe event (by ordinal among probe events) belongs to the latest submission.
  const [draft, setDraft] = useState("");
  const [recipient, setRecipient] = useState<string>(RECIPIENTS[0]);
  const [lang, setLang] = useState<"en" | "ar">(locale === "ar" ? "ar" : "en");
  const [emptyError, setEmptyError] = useState(false);
  const [probeOrdinal, setProbeOrdinal] = useState<number | null>(null);
  const probe = useMutation({
    mutationFn: postGateProbe,
    onSuccess: () => void events.refetch(),
  });
  const result: GateResult | undefined = probe.data;

  const matched = useMemo(() => {
    if (probeOrdinal === null) return null;
    let seen = 0;
    for (let i = 0; i < list.length; i++) {
      if (list[i].message_id === "probe") {
        if (seen === probeOrdinal) return i;
        seen++;
      }
    }
    return null;
  }, [list, probeOrdinal]);

  const shown = list.slice(-SHOW);
  const offset = list.length - shown.length;
  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [list.length]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim()) {
      setEmptyError(true);
      return;
    }
    setEmptyError(false);
    setProbeOrdinal(probeCount);
    probe.mutate({ recipient_partner_id: recipient, draft, lang });
  };

  const live = events.isSuccess && !events.isError;
  const matchedEvent = matched !== null ? list[matched] : null;

  return (
    <div className="grid gap-6 xl:grid-cols-12">
      {/* Terminal */}
      <div className="xl:col-span-7" data-testid="terminal">
        <div className="overflow-hidden rounded-xl border border-line-strong bg-black">
          <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2">
            <p className="font-mono text-xs text-ink-2">bioethics-supervisor · {API_BASE}/api/guardrail/events</p>
            <StatusChip status={live ? "compatible" : "neutral"} size="sm">
              {live ? t("liveBadge") : t("pausedBadge")}
            </StatusChip>
          </div>
          <div
            ref={scroller}
            tabIndex={0}
            role="region"
            aria-label={t("region")}
            className="max-h-[28rem] min-h-[20rem] overflow-y-auto p-4 font-mono text-sm leading-relaxed"
            dir="ltr"
          >
            <ul>
              <PackLines />
              <li className="mt-3 text-ink">$ tail -f /api/guardrail/events</li>
              {events.isPending ? <li className="text-ink-2">… {t("connecting", { api: API_BASE })}</li> : null}
              {events.isError ? (
                <li className="text-review-ink" data-testid="feed-offline">
                  ! {t("offline", { api: API_BASE })}
                </li>
              ) : null}
              {live && list.length === 0 ? <li className="text-ink-2">· {t("empty")}</li> : null}
              {shown.map((e, i) => {
                const idx = offset + i;
                const mine = idx === matched;
                return (
                  <li
                    key={idx}
                    data-testid={mine ? "feed-probe-event" : "feed-event"}
                    data-outcome={e.outcome}
                    className={mine ? "-mx-2 rounded bg-lime/15 px-2 outline outline-1 outline-lime" : undefined}
                  >
                    <span className="text-ink-2">{e.ts}</span> <span className={TONE[e.outcome]}>{GLYPH[e.outcome]} {e.outcome}</span>{" "}
                    <span className="text-ink">{e.rule}</span> <span className="text-ink-2">· {e.message_id}</span>
                    {mine ? <span className="ms-2 font-semibold text-lime">◀ {t("highlight")}</span> : null}
                  </li>
                );
              })}
            </ul>
          </div>
          <p className="border-t border-line px-4 py-2 font-mono text-xs text-ink-2" aria-live="polite">
            {live ? t("count", { n: list.length }) : ""}
          </p>
        </div>
      </div>

      {/* Gate probe */}
      <Card variant="raised" className="space-y-5 xl:col-span-5" aria-labelledby="probe-h" data-testid="gate-probe">
        <div className="space-y-1">
          <h3 id="probe-h" className="font-display text-xl font-semibold text-ink">
            {tp("title")}
          </h3>
          <p className="text-sm text-ink-2">{tp("description")}</p>
        </div>
        <form onSubmit={submit} className="space-y-4" noValidate>
          <FormField label={tp("draft")} help={tp("draftHelp")} error={emptyError ? tp("empty") : undefined} required>
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={5}
              data-testid="probe-draft"
              dir="auto"
              lang={lang}
            />
          </FormField>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label={tp("recipient")}>
              <Select
                value={recipient}
                onValueChange={setRecipient}
                options={RECIPIENTS.map((id) => ({ value: id, label: tp("recipientOption", { id, v: id.slice(1, 2), role: id.slice(2) }) }))}
                aria-label={tp("recipient")}
              />
            </FormField>
            <FormField label={tp("lang")}>
              <Select
                value={lang}
                onValueChange={(v) => setLang(v === "ar" ? "ar" : "en")}
                options={[
                  { value: "en", label: tp("en") },
                  { value: "ar", label: tp("ar") },
                ]}
                aria-label={tp("lang")}
              />
            </FormField>
          </div>
          <Button type="submit" variant="lime" loading={probe.isPending} data-testid="probe-submit">
            {probe.isPending ? tp("running") : tp("submit")}
          </Button>
        </form>

        <div aria-live="polite" className="space-y-3" data-testid="probe-result">
          {probe.isError ? (
            <p className="rounded-lg border border-review/60 bg-review/10 p-4 text-sm text-ink" data-testid="probe-error">
              {probe.error instanceof ApiError && probe.error.status === 404 ? tp("notFound") : tp("error", { api: API_BASE })}
            </p>
          ) : null}
          {result && !probe.isPending ? (
            result.passed ? (
              <div className="space-y-2 rounded-lg border border-info/50 bg-info/10 p-4" data-testid="probe-passed">
                <p className="font-semibold text-ink">{tp("passed")}</p>
                <p className="text-sm text-ink">{tp("passedBody")}</p>
              </div>
            ) : (
              <GuardBanner title={tp("held")} testId="probe-held">
                <p>{tp("heldBody")}</p>
                <p className="mt-3 font-semibold">{tp("rules")}</p>
                <ul className="mt-1 space-y-1" data-testid="probe-rules">
                  {result.violations.map((v, i) => (
                    <li key={i} className="flex flex-wrap items-baseline gap-2">
                      <span className="rounded-sm border border-line-strong px-1.5 font-mono text-xs font-semibold text-ink" data-rule={v.rule}>
                        {v.rule}
                      </span>
                      <span className="text-xs text-ink-2" dir="auto">
                        {v.detail}
                      </span>
                    </li>
                  ))}
                </ul>
              </GuardBanner>
            )
          ) : null}
          {result && !probe.isPending ? (
            <p className="font-mono text-xs text-ink-2" data-testid="probe-event">
              {tp("event")}:{" "}
              {matchedEvent ? (
                <span className="text-ink" dir="ltr">
                  {matchedEvent.ts} · {matchedEvent.outcome} · {matchedEvent.rule}
                </span>
              ) : (
                tp("eventPending")
              )}
            </p>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
