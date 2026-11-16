"use client";
// Timeline: the 7-state care loop plus the case's audit events (ids and actions only, no PHI).
// The shared CareTimeline shows a state the loop jumped past as "Skipped", never as done (P-04, DECISIONS #50).
import { CareTimeline, Card, CardHeader, Timeline, useUI, type TimelineItem } from "@evolve/ui";
import { useTranslations } from "next-intl";
import type { CaseView, LoopState } from "@/lib/types";
import { LOOP_STATES } from "@/lib/types";
import { useFormatTs } from "../format";
import { useCoupleStatusLabel } from "../Workbench";

export function TimelineTab({ view }: { view: CaseView }) {
  const t = useTranslations("timeline");
  const { labels } = useUI();
  const formatTs = useFormatTs();
  const statusLabel = useCoupleStatusLabel();
  const state = view.case.couple_status;
  const isLoop = (LOOP_STATES as readonly string[]).includes(state);
  const history = view.timeline
    .filter((e): e is Extract<CaseView["timeline"][number], { kind: "loop" }> => e.kind === "loop")
    .map((e) => ({ state: e.state, ts: e.ts, actor_role: e.actor_role }));

  const actionLabel = (a: string) => {
    const k = `actions.${a.replace(/\./g, "_")}` as "actions.note_create";
    return t.has(k) ? t(k) : a;
  };
  const actor = (r: string) => (t.has(`actors.${r}` as "actors.system") ? t(`actors.${r}` as "actors.system") : r);
  const items: TimelineItem[] = view.timeline.map((e, i) => ({
    key: `${e.ts}-${i}`,
    status: "complete",
    ts: e.ts,
    title: e.kind === "loop" ? t("loopEntry", { state: labels.loopStates[e.state] }) : actionLabel(e.action),
    owner: e.kind === "loop" ? actor(e.actor_role) : undefined,
  }));

  return (
    <div className="grid gap-5 lg:grid-cols-2" data-testid="timeline">
      <Card>
        <CardHeader title={t("loop")} level={2} />
        {isLoop ? (
          <CareTimeline state={state as LoopState} history={history} ownerFor={(s) => t(`owner.${s}`)} formatTs={formatTs} label={t("loop")} />
        ) : (
          <p className="text-sm text-ink-2">{statusLabel(state)}</p>
        )}
      </Card>
      <Card>
        <CardHeader title={t("activity")} level={2} />
        {items.length ? <Timeline items={items} label={t("activity")} formatTs={formatTs} /> : <p className="text-sm text-ink-2">{t("activityEmpty")}</p>}
      </Card>
    </div>
  );
}
