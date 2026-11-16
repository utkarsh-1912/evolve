"use client";
// Citizen AppShell (docs/09 §3): sidebar, top bar (title + breadcrumb, language, notifications, profile),
// context strip (person · couple status · consent), mobile bottom tabs + "More", shell footer with the
// compliance line. Replaces the P2 pill nav and floating footer chip (A1, A2).
import { Button } from "@evolve/ui/primitives/button";
import { AppShell, ContextStrip, ShellFooter, TopBar, type NavItem } from "@evolve/ui/shell/app-shell";
import { Rail } from "@evolve/ui/shell/rail";
import { ContextChip } from "@evolve/ui/shell/hints";
import { BottomTabs } from "@evolve/ui/shell/bottom-tabs";
import { LangSwitch } from "@evolve/ui/shell/lang-switch";
import { NotificationBell } from "@evolve/ui/shell/notification-bell";
import { ProfileMenu } from "@evolve/ui/shell/profile-menu";
import { Bell, CalendarCheck2, FileHeart, HeartHandshake, HelpCircle, Home, LayoutTemplate, LogOut, ShieldCheck, ShieldOff, UserRound, UserRoundCog, Users } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { useHome, useMarkAllNotificationsRead, useNotifications, useSignOut } from "@/lib/queries";
import { useSession } from "@/lib/session";
import type { CoupleStatus } from "@/lib/types";
import { BrandLogo } from "./BrandLogo";
import { useApiText } from "./app-helpers";

const COUPLE_TONE: Record<CoupleStatus, "neutral" | "info" | "review"> = {
  not_linked: "neutral",
  invited: "review",
  both_consented: "info",
  result_ready: "info",
};

export function useFormatTs() {
  const locale = useLocale();
  return (iso: string) =>
    new Intl.DateTimeFormat(locale === "ar" ? "ar-AE-u-nu-latn" : "en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
}

export function CitizenShell({ children }: { children: ReactNode }) {
  const t = useTranslations("chrome");
  const pathname = usePathname();
  const router = useRouter();
  const { session } = useSession();
  const signOut = useSignOut();
  const home = useHome();
  const notifications = useNotifications();
  const markAll = useMarkAllNotificationsRead();
  const formatTs = useFormatTs();
  const api = useApiText();
  const other = t("lang.switchToLang");

  const is = (p: string) => pathname === p || pathname.startsWith(`${p}/`);
  const nav: NavItem[] = [
    { key: "home", href: "/home", label: t("nav.home"), icon: Home, active: is("/home") },
    { key: "results", href: "/results", label: t("nav.results"), icon: FileHeart, active: is("/results") },
    { key: "compatibility", href: "/compatibility", label: t("nav.compatibility"), icon: HeartHandshake, active: is("/compatibility") },
    { key: "care", href: "/care-plan", label: t("nav.care"), icon: CalendarCheck2, active: is("/care-plan") || is("/teachback") },
    { key: "family", href: "/family", label: t("nav.family"), icon: Users, active: is("/family") },
    { key: "privacy", href: "/privacy", label: t("nav.privacy"), icon: ShieldCheck, active: is("/privacy") },
    { key: "help", href: "/help", label: t("nav.help"), icon: HelpCircle, active: is("/help") },
  ];
  const byKey = Object.fromEntries(nav.map((n) => [n.key, n]));
  const tabs: NavItem[] = [byKey.home, byKey.results, byKey.compatibility, { ...byKey.care, label: t("nav.careShort") }];
  const more: NavItem[] = [
    byKey.family,
    byKey.privacy,
    { key: "notifications", href: "/notifications", label: t("nav.notifications"), icon: Bell, active: is("/notifications") },
    byKey.help,
  ];

  const page = (title: string, crumbs: { label: string; href?: string }[] = [{ label: title }]) => ({ title, crumbs });
  const route: Record<string, { title: string; crumbs: { label: string; href?: string }[] }> = {
    "/home": page(t("nav.home")),
    "/results": page(t("nav.results")),
    "/results/explainer": page(t("nav.explainer"), [{ label: t("nav.results"), href: "/results" }, { label: t("nav.explainer") }]),
    "/compatibility": page(t("nav.compatibility")),
    "/teachback": page(t("nav.teachback"), [{ label: t("nav.care"), href: "/care-plan" }, { label: t("nav.teachback") }]),
    "/care-plan": page(t("nav.care")),
    "/family": page(t("nav.family")),
    "/privacy": page(t("nav.privacy")),
    "/notifications": page(t("nav.notifications")),
    "/help": page(t("nav.help")),
  };
  const current = route[pathname] ?? { title: "évolvé", crumbs: [] };

  const h = home.data;
  // §10.3 compact chips: icon + 1–2 words; full detail in tooltip and screen-reader text.
  const contextItems = session
    ? [
        {
          key: "person",
          label: t("context.person"),
          value: <ContextChip icon={UserRound} label={session.partner_id} detail={t("context.syntheticPerson", { id: session.partner_id })} testId="chip-person" />,
        },
        {
          key: "couple",
          label: t("context.couple"),
          value: h ? (
            <ContextChip
              icon={HeartHandshake}
              label={t(`context.status.${h.couple_status}`)}
              detail={`${t("context.couple")}: ${t(`context.status.${h.couple_status}`)}`}
              tone={COUPLE_TONE[h.couple_status]}
              testId="chip-couple"
            />
          ) : (
            <span className="text-ink-2">…</span>
          ),
        },
        {
          key: "consent",
          label: t("context.consent"),
          value: h ? (
            h.consent && h.consent.status === "active" ? (
              <ContextChip
                icon={ShieldCheck}
                label={t("context.consentShort")}
                detail={t("context.consentActive", { time: formatTs(h.consent.expires_at) })}
                tone="info"
                testId="chip-consent"
              />
            ) : (
              <ContextChip icon={ShieldOff} label={t("context.consentNone")} detail={`${t("context.consent")}: ${t("context.consentNone")}`} testId="chip-consent" />
            )
          ) : (
            <span className="text-ink-2">…</span>
          ),
        },
      ]
    : [{ key: "person", label: t("context.person"), value: <ContextChip icon={UserRound} label={t("context.notSignedIn")} /> }];

  const notes = (notifications.data ?? []).map((n) => ({
    id: n.id,
    title: api(n.title_key),
    ts: n.ts,
    href: n.href,
    read: n.read,
  }));

  const actions = (
    <>
      <LangSwitch href={`/${other}${pathname === "/" ? "" : pathname}`} label={t("lang.switchTo")} lang={other} compact />
      {session ? (
        <>
          <NotificationBell
            items={notes}
            loading={notifications.isLoading}
            formatTs={formatTs}
            onMarkAllRead={() => markAll.mutate(notes.filter((n) => !n.read).map((n) => n.id))}
            footer={
              <Link href="/notifications" className="inline-flex min-h-11 items-center text-sm font-semibold text-navy underline-offset-4 hover:underline">
                {t("viewAll")}
              </Link>
            }
          />
          <ProfileMenu
            name={session.partner_id}
            detail={t("context.syntheticPerson", { id: session.partner_id })}
            items={[
              { label: t("switchPerson"), href: "/sign-in", icon: <UserRoundCog aria-hidden /> },
              { label: t("designSystem"), href: "/design-system", icon: <LayoutTemplate aria-hidden /> },
              "separator",
              {
                label: t("signOut"),
                icon: <LogOut aria-hidden />,
                onSelect: () => {
                  signOut();
                  router.push("/sign-in");
                },
              },
            ]}
          />
        </>
      ) : (
        <Button asChild size="sm">
          <Link href="/sign-in">{t("signIn")}</Link>
        </Button>
      )}
    </>
  );

  return (
    <AppShell
      sidebar={<Rail logo={<BrandLogo height={32} />} mark={<BrandLogo variant="mark" height={32} />} items={nav} storageKey="evolve.rail.citizen" />}
      topBar={<TopBar title={current.title} breadcrumbs={current.crumbs} mobileLogo={<span className="grid size-11 place-items-center rounded-md bg-navy"><BrandLogo variant="mark" height={28} /></span>} actions={actions} />}
      contextStrip={<ContextStrip label={t("context.label")} items={contextItems} />}
      bottomTabs={<BottomTabs items={tabs} more={more} />}
      footer={<ShellFooter compliance={t("compliance")} environment={t("footerEnv")} />}
      theme="clinic"
    >
      {children}
    </AppShell>
  );
}
