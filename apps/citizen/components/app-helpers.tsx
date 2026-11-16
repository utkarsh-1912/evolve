"use client";
// Shared citizen-app helpers: session guard, API i18n keys, date formatting, activity lines, counselor rail.
import { Button } from "@evolve/ui/primitives/button";
import { Card, CardHeader } from "@evolve/ui/primitives/display";
import { Skeleton } from "@evolve/ui/primitives/feedback";
import { ArrowRight, UserRoundCheck } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { Link } from "@/i18n/navigation";
import { useHome } from "@/lib/queries";
import { useSession } from "@/lib/session";
import type { ActivityEvent } from "@/lib/types";
import { SignInRequired } from "./SignInRequired";

/** Renders children only for a signed-in partner; otherwise the permission state (docs/09 §6). */
export function RequireSession({ title, body, children }: { title: string; body: string; children: ReactNode }) {
  const { session, ready } = useSession();
  if (!ready) return null;
  if (!session) return <SignInRequired title={title} body={body} />;
  return <>{children}</>;
}

/** Text for an i18n key returned by the API (title_key/body_key/note_key). UI owns wording (api.md v1.2.0). */
export function useApiText() {
  const t = useTranslations("api");
  return (key: string) => (t.has(key) ? t(key) : key);
}

export function useFormat() {
  const locale = useLocale();
  const tag = locale === "ar" ? "ar-AE-u-nu-latn" : "en-GB";
  return {
    dateTime: (iso: string) => new Intl.DateTimeFormat(tag, { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso)),
    date: (iso: string) => new Intl.DateTimeFormat(tag, { dateStyle: "medium" }).format(new Date(iso)),
  };
}

/** One plain sentence per own AuditEvent ("You viewed your results"). Unknown vocab falls back safely. */
export function useActivityLine() {
  const t = useTranslations("activity");
  return (e: ActivityEvent) => {
    const who = t.has(`who.${e.actor_role}`) ? t(`who.${e.actor_role}`) : e.actor_role;
    const action = t.has(`action.${e.action}`) ? t(`action.${e.action}`) : t("action.other");
    const object = t.has(`object.${e.object_kind}`) ? t(`object.${e.object_kind}`) : t("object.other");
    return t("line", { who, action, object });
  };
}

/** "Your counselor / next step" rail (orchestrator review, DECISIONS #44): fills the right column under Sharing & consent. */
export function CounselorRail() {
  const t = useTranslations("compat");
  const api = useApiText();
  const home = useHome();
  const step = home.data?.next_step;
  return (
    <Card data-testid="counselor-rail">
      <CardHeader title={t("counselorTitle")} />
      <p className="flex items-start gap-3 text-sm text-ink">
        <UserRoundCheck aria-hidden className="mt-0.5 size-5 shrink-0 text-navy" />
        {t("counselorBody")}
      </p>
      <div className="mt-4 border-t border-line pt-4">
        <p className="text-sm font-semibold text-ink-2">{t("counselorNext")}</p>
        {step ? (
          <Button asChild variant="secondary" block className="mt-2 justify-between">
            <Link href={step.href} data-testid="rail-next-step">
              <span>{api(step.title_key)}</span>
              <ArrowRight aria-hidden className="size-4 rtl:-scale-x-100" />
            </Link>
          </Button>
        ) : (
          <Skeleton className="mt-2 h-11" />
        )}
      </div>
    </Card>
  );
}
