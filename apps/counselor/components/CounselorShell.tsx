"use client";
// Counselor AppShell (docs/09 §3 + §10 clean UI, Ledger theme).
// - Collapsible icon rail: Queue, Cases, Calendar (SIMULATED), Reports.
// - Top bar: case-ID search; the shift toggle keeps a visible text state; density, language and profile are icons.
// - Context chips: counselor, shift, scopes.
// - Footer: compliance line, always text.
import { Button, Switch, useToast } from "@evolve/ui";
import { AppShell, ContextStrip, ShellFooter, TopBar, type NavItem } from "@evolve/ui/shell/app-shell";
import { BottomTabs } from "@evolve/ui/shell/bottom-tabs";
import { ContextChip, IconAction } from "@evolve/ui/shell/hints";
import { LangSwitch } from "@evolve/ui/shell/lang-switch";
import { ProfileMenu } from "@evolve/ui/shell/profile-menu";
import { Rail } from "@evolve/ui/shell/rail";
import { BarChart3, CalendarDays, FolderOpen, KeyRound, LayoutTemplate, ListTodo, LogOut, Power, PowerOff, Rows3, Rows4, UserRound } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, type ReactNode } from "react";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { useDensity } from "@/lib/prefs";
import { useShift, useSignOut } from "@/lib/queries";
import { useSession } from "@/lib/session";
import { BrandLogo } from "./BrandLogo";
import { CaseSearch } from "./CaseSearch";

export function CounselorShell({ children }: { children: ReactNode }) {
  const t = useTranslations("chrome");
  const pathname = usePathname();
  const router = useRouter();
  const { session } = useSession();
  const signOut = useSignOut();
  const shift = useShift();
  const toast = useToast();
  const [density, setDensity] = useDensity();
  const shiftId = useId();
  const other = t("lang.switchToLang");

  const is = (p: string) => pathname === p || pathname.startsWith(`${p}/`);
  const nav: NavItem[] = [
    { key: "queue", href: "/queue", label: t("nav.queue"), icon: ListTodo, active: is("/queue") },
    { key: "cases", href: "/cases", label: t("nav.cases"), icon: FolderOpen, active: is("/cases") },
    { key: "calendar", href: "/calendar", label: t("nav.calendar"), icon: CalendarDays, active: is("/calendar") },
    { key: "reports", href: "/reports", label: t("nav.reports"), icon: BarChart3, active: is("/reports") },
  ];

  const title = is("/queue")
    ? t("nav.queue")
    : is("/cases")
      ? t("nav.cases")
      : is("/calendar")
        ? t("nav.calendar")
        : is("/reports")
          ? t("nav.reports")
          : t("nav.designSystem");
  // Breadcrumb only when there is a parent (case detail); the title is not repeated (§10.2).
  const crumbs = pathname.startsWith("/cases/")
    ? [{ label: t("nav.cases"), href: "/cases" }, { label: decodeURIComponent(pathname.slice("/cases/".length)) }]
    : undefined;

  const onShift = !!session?.on_shift;
  const toggleShift = (on: boolean) =>
    shift.mutate(on, {
      onSuccess: () => toast({ title: on ? t("shift.turnedOn") : t("shift.turnedOff"), tone: on ? "success" : "info" }),
    });

  const actions = (
    <>
      {session ? <CaseSearch className="hidden lg:block" /> : null}
      {session ? (
        // Shift is access-critical: the state stays visible as text, not icon-only.
        <div className="flex items-center gap-2 px-1" data-testid="shift-toggle">
          <Switch
            id={shiftId}
            aria-label={t("shift.label")}
            checked={onShift}
            disabled={shift.isPending}
            onCheckedChange={toggleShift}
            data-testid="shift-switch"
          />
          <label htmlFor={shiftId} className="cursor-pointer text-sm font-semibold text-ink" data-testid="shift-text">
            {onShift ? t("shift.on") : t("shift.off")}
          </label>
        </div>
      ) : null}
      <IconAction
        label={`${t("density.label")}: ${density === "compact" ? t("density.compact") : t("density.comfortable")}`}
        icon={density === "compact" ? Rows4 : Rows3}
        aria-pressed={density === "compact"}
        onClick={() => setDensity(density === "compact" ? "comfortable" : "compact")}
        tipSide="bottom"
        data-testid="density-toggle"
      />
      <LangSwitch href={`/${other}${pathname === "/" ? "" : pathname}`} label={t("lang.switchTo")} lang={other} compact />
      {session ? (
        <ProfileMenu
          name={session.counselor_id}
          detail={t("context.accessScopes")}
          items={[
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
      ) : (
        <Button asChild size="sm">
          <Link href="/sign-in">{t("signIn")}</Link>
        </Button>
      )}
    </>
  );

  const contextItems = session
    ? [
        {
          key: "counselor",
          label: t("context.counselor"),
          value: <ContextChip icon={UserRound} label={session.counselor_id} detail={`${t("context.counselor")}: ${session.counselor_id}`} testId="chip-counselor" />,
        },
        {
          key: "shift",
          label: t("context.shift"),
          value: (
            <ContextChip
              icon={onShift ? Power : PowerOff}
              label={<span data-testid="shift-status">{onShift ? t("shift.on") : t("shift.off")}</span>}
              detail={onShift ? t("shift.turnedOn") : t("shift.turnedOff")}
              tone={onShift ? "info" : "neutral"}
              testId="chip-shift"
            />
          ),
        },
        {
          key: "access",
          label: t("context.access"),
          value: <ContextChip icon={KeyRound} label={t("context.scopesShort")} detail={`${t("context.accessScopes")}: ${session.scopes.join(" ")}`} testId="chip-scopes" />,
        },
      ]
    : [{ key: "counselor", label: t("context.counselor"), value: <ContextChip icon={UserRound} label={t("context.notSignedIn")} /> }];

  return (
    <div data-density={density}>
      <div aria-hidden className="ledger-grain pointer-events-none fixed inset-0 z-[1]" />
      <AppShell
        theme="ledger"
        sidebar={<Rail logo={<BrandLogo height={32} />} mark={<BrandLogo variant="mark" height={32} />} items={nav} storageKey="evolve.rail.counselor" />}
        topBar={
          <TopBar
            title={title}
            breadcrumbs={crumbs}
            mobileLogo={
              <span className="grid size-11 place-items-center rounded-md bg-navy">
                <BrandLogo variant="mark" height={28} />
              </span>
            }
            actions={actions}
          />
        }
        contextStrip={<ContextStrip label={t("context.label")} items={contextItems} />}
        bottomTabs={<BottomTabs items={nav} />}
        footer={<ShellFooter compliance={t("compliance")} environment={t("footerEnv")} />}
      >
        {children}
      </AppShell>
    </div>
  );
}
