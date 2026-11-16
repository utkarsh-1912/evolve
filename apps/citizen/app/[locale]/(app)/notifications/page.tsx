"use client";
// Notifications inbox (docs/09 §4.1-9): each item links to its surface; mark read; wording from title_key.
import { Card } from "@evolve/ui/primitives/display";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@evolve/ui/primitives/feedback";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { BellOff, CheckCheck, ChevronRight } from "lucide-react";
import { IconAction } from "@evolve/ui/shell/hints";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useMarkAllNotificationsRead, useNotifications } from "@/lib/queries";
import { RequireSession, useApiText, useFormat } from "@/components/app-helpers";

export default function NotificationsPage() {
  const t = useTranslations("notifications");
  return (
    <RequireSession title={t("signInTitle")} body={t("signInBody")}>
      <Inner />
    </RequireSession>
  );
}

function Inner() {
  const t = useTranslations("notifications");
  const api = useApiText();
  const f = useFormat();
  const list = useNotifications();
  const markAll = useMarkAllNotificationsRead();
  const unread = (list.data ?? []).filter((n) => !n.read);
  return (
    <>
      <PageHeader
        title={t("title")}
        description={t("description")}
        actions={
          unread.length ? (
            <IconAction label={t("markAll")} icon={CheckCheck} variant="secondary" disabled={markAll.isPending} onClick={() => markAll.mutate(unread.map((n) => n.id))} data-testid="mark-all" />
          ) : null
        }
      />
      {list.isLoading ? (
        <LoadingRegion>
          <div className="space-y-3">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
        </LoadingRegion>
      ) : list.isError ? (
        <ErrorState onRetry={() => list.refetch()} reference="NOTIFICATIONS-LOAD" />
      ) : !list.data?.length ? (
        <EmptyState icon={BellOff} title={t("empty")} testId="notifications-empty" />
      ) : (
        <Card padding="none" className="max-w-3xl overflow-hidden">
          <ul className="divide-y divide-line" data-testid="notification-list">
            {list.data.map((n) => (
              <li key={n.id}>
                <Link href={n.href} className="flex min-h-16 items-center gap-4 px-5 py-3 hover:bg-surface-2">
                  <span aria-hidden className={`size-2.5 shrink-0 rounded-full ${n.read ? "bg-transparent" : "bg-navy"}`} />
                  <span className="min-w-0 flex-1">
                    <span className={`block ${n.read ? "text-ink-2" : "font-semibold text-ink"}`}>
                      {api(n.title_key)}
                      {!n.read ? <span className="sr-only"> ({t("unread")})</span> : null}
                    </span>
                    <time dateTime={n.ts} className="text-sm text-ink-2">
                      {f.dateTime(n.ts)}
                    </time>
                  </span>
                  <ChevronRight aria-hidden className="size-5 text-ink-2 rtl:-scale-x-100" />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
