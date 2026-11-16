"use client";
// Home dashboard (docs/09 §4.1-1): greeting, one "Your next step" hero chosen by the backend's loop state,
// status cards, and recent own activity (AuditEvents, no genes, no counterpart identity).
import { Button } from "@evolve/ui/primitives/button";
import { Card, CardHeader, StatusChip, type Status } from "@evolve/ui/primitives/display";
import { EmptyState, ErrorState, LoadingRegion, SimulatedBadge, Skeleton } from "@evolve/ui/primitives/feedback";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { ArrowRight, CalendarCheck2, FileHeart, HeartHandshake, History } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useActivity, useCarePlan, useHome } from "@/lib/queries";
import { useSession } from "@/lib/session";
import type { CoupleStatus } from "@/lib/types";
import { RequireSession, useActivityLine, useApiText, useFormat } from "@/components/app-helpers";

const COUPLE_TONE: Record<CoupleStatus, Status> = { not_linked: "neutral", invited: "review", both_consented: "info", result_ready: "info" };

export default function HomePage() {
  const t = useTranslations("home");
  return (
    <RequireSession title={t("title")} body={useTranslations("results")("signInBody")}>
      <HomeInner />
    </RequireSession>
  );
}

function HomeInner() {
  const t = useTranslations("home");
  const tc = useTranslations("chrome");
  const tui = useTranslations("ui");
  const api = useApiText();
  const line = useActivityLine();
  const f = useFormat();
  const { session } = useSession();
  const home = useHome();
  const care = useCarePlan();
  const activity = useActivity(6);

  return (
    <>
      <PageHeader title={t("greeting", { id: session?.partner_id ?? "" })} description={t("description")} badge={<SimulatedBadge label={tc("simulated")} />} />
      {home.isError ? (
        <ErrorState onRetry={() => home.refetch()} reference="HOME-LOAD" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-8">
            {home.data ? (
              <Card variant="inverse" padding="lg" data-testid="next-step">
                <p className="text-sm font-semibold text-lime">{t("nextStep")}</p>
                <h2 className="mt-2 font-display text-[1.875rem] font-medium leading-tight">{api(home.data.next_step.title_key)}</h2>
                <Button asChild variant="lime" size="lg" className="mt-5">
                  <Link href={home.data.next_step.href} data-testid="next-step-cta">
                    {t("go")}
                    <ArrowRight aria-hidden className="size-5 rtl:-scale-x-100" />
                  </Link>
                </Button>
              </Card>
            ) : (
              <LoadingRegion>
                <Skeleton className="h-48" rounded="lg" />
              </LoadingRegion>
            )}

            <div className="grid gap-4 sm:grid-cols-3">
              <StatusCard href="/results" icon={<FileHeart aria-hidden className="size-5" />} title={t("results")} loading={!home.data}>
                {home.data ? t("resultsCount", { count: home.data.counts.results }) : null}
              </StatusCard>
              <StatusCard href="/compatibility" icon={<HeartHandshake aria-hidden className="size-5" />} title={t("compatibility")} loading={!home.data}>
                {home.data ? (
                  <StatusChip status={COUPLE_TONE[home.data.couple_status]} size="sm">
                    {tc(`context.status.${home.data.couple_status}`)}
                  </StatusChip>
                ) : null}
              </StatusCard>
              <StatusCard href="/care-plan" icon={<CalendarCheck2 aria-hidden className="size-5" />} title={t("care")} loading={!care.data}>
                {care.data ? (care.data.loop.state ? tui(`loopStates.${care.data.loop.state}`) : t("careNone")) : null}
              </StatusCard>
            </div>
          </div>

          <Card as="aside" className="lg:col-span-4" aria-labelledby="activity-h">
            <CardHeader id="activity-h" title={t("activity")} />
            {activity.isLoading ? (
              <LoadingRegion>
                <div className="space-y-3">
                  <Skeleton className="h-10" />
                  <Skeleton className="h-10" />
                  <Skeleton className="h-10" />
                </div>
              </LoadingRegion>
            ) : activity.data && activity.data.length ? (
              <ol className="space-y-3" data-testid="activity-list">
                {activity.data.map((e) => (
                  <li key={`${e.ts}-${e.action}-${e.object_kind}`} className="flex gap-3 text-sm">
                    <History aria-hidden className="mt-0.5 size-4 shrink-0 text-ink-2" />
                    <span>
                      <span className="block text-ink">{line(e)}</span>
                      <time dateTime={e.ts} className="text-ink-2">
                        {f.dateTime(e.ts)}
                      </time>
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState icon={History} title={t("activityEmpty")} />
            )}
            <Link href="/privacy" className="mt-4 inline-flex min-h-11 items-center text-sm font-semibold text-navy underline-offset-4 hover:underline">
              {t("activityAll")}
            </Link>
          </Card>
        </div>
      )}
    </>
  );
}

function StatusCard({ href, icon, title, loading, children }: { href: string; icon: React.ReactNode; title: string; loading: boolean; children: React.ReactNode }) {
  return (
    <Link href={href} className="group block rounded-xl border border-line bg-surface-1 p-5 transition-shadow hover:shadow-e2">
      <span className="flex items-center justify-between gap-2 text-sm font-semibold text-ink-2">
        {title}
        <span className="grid size-9 place-items-center rounded-md bg-surface-2 text-navy">{icon}</span>
      </span>
      <span className="mt-3 block min-h-8 text-lg font-semibold text-ink">{loading ? <Skeleton className="h-7 w-2/3" /> : children}</span>
    </Link>
  );
}
