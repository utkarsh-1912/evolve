"use client";
// Eval dashboard shell (clean-UI Wave B, docs/09 §10, NOTE-UI-SHELL): collapsible icon rail whose items are the
// page sections (scroll-spy keeps the lime "you are here" bar), icon-only language switch in the top bar, compact
// provenance chips (detail in tooltip + sr-only text), compliance line in the shell footer (never icon-only).
import { AppShell, ContextStrip, ShellFooter, TopBar, type NavItem } from "@evolve/ui/shell/app-shell";
import { ContextChip } from "@evolve/ui/shell/hints";
import { LangSwitch } from "@evolve/ui/shell/lang-switch";
import { Rail } from "@evolve/ui/shell/rail";
import { useQuery } from "@tanstack/react-query";
import { FileText, Gauge, Grid3x3, ListChecks, Lock, Package, RefreshCw, Scale, ShieldCheck, SquareTerminal, Users, Wifi, WifiOff, type LucideIcon } from "lucide-react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";
import { API_BASE, getGuardrailEvents } from "@/lib/api";
import { cohort, evidence } from "@/lib/evidence";
import { utc } from "@/lib/format";

export const SECTIONS: { id: string; icon: LucideIcon }[] = [
  { id: "simreal", icon: Scale },
  { id: "dimensions", icon: Gauge },
  { id: "gate", icon: ShieldCheck },
  { id: "leakage", icon: Lock },
  { id: "cohort", icon: Grid3x3 },
  { id: "tests", icon: ListChecks },
  { id: "probe", icon: SquareTerminal },
  { id: "assumptions", icon: FileText },
];

function useActiveSection() {
  const [active, setActive] = useState<string>(SECTIONS[0].id);
  useEffect(() => {
    const els = SECTIONS.map((s) => document.getElementById(s.id)).filter((e): e is HTMLElement => !!e);
    const io = new IntersectionObserver(
      (entries) => {
        const hit = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (hit) setActive(hit.target.id);
      },
      { rootMargin: "-30% 0px -60% 0px" },
    );
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);
  return active;
}

function Logo({ variant }: { variant: "lockup" | "mark" }) {
  const t = useTranslations("chrome");
  const mark = variant === "mark";
  // Re-cut assets (docs/09 §10), on the navy rail only. Aspect ratios from the files (411×132 lockup, 133×132 mark).
  return (
    <Image
      src={mark ? "/brand/evolve-mark-transparent.png" : "/brand/evolve-logo-transparent.png"}
      alt={t("logoAlt")}
      width={mark ? 32 : 100}
      height={32}
      priority
      style={{ width: mark ? 32 : 100, height: 32 }}
    />
  );
}

const shortDate = (iso: string) => new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(iso));

export function EvalShell({ children }: { children: ReactNode }) {
  const t = useTranslations("chrome");
  const ts = useTranslations("sections");
  const th = useTranslations("header");
  const active = useActiveSection();
  // Shares the React Query cache with the terminal (same key), so this adds no extra polling.
  const feed = useQuery({ queryKey: ["guardrail-events"], queryFn: getGuardrailEvents, refetchInterval: 2000, retry: false });
  const pr = evidence.persona_runs;

  const nav: NavItem[] = SECTIONS.map((s) => ({ key: s.id, href: `#${s.id}`, label: ts(s.id), icon: s.icon, active: active === s.id }));

  const chips = [
    {
      key: "pack",
      value: (
        <ContextChip
          icon={Package}
          label={th("chipPack", { date: shortDate(evidence.build.utc) })}
          detail={th("chipPackDetail", { ts: utc(evidence.build.utc), digest: evidence.build.contracts_sha256.slice(0, 16), source: th("source") })}
          testId="chip-pack"
        />
      ),
    },
    {
      key: "runs",
      value: (
        <ContextChip
          icon={Users}
          label={th("chipRuns", { n: pr.n })}
          detail={th("chipRunsDetail", { n: pr.n, perStratum: pr.per_stratum, strata: pr.strata, seed: pr.seed, problems: pr.harness_problems.length })}
          testId="chip-runs"
        />
      ),
    },
    {
      key: "sync",
      value: (
        <ContextChip
          icon={RefreshCw}
          label={th("chipSync", { date: shortDate(cohort.generated_utc) })}
          detail={th("chipSyncDetail", { ts: utc(cohort.generated_utc) })}
          testId="chip-sync"
        />
      ),
    },
    {
      key: "feed",
      value: feed.isSuccess ? (
        <ContextChip icon={Wifi} label={th("liveChip")} detail={th("liveDetail", { api: API_BASE })} tone="info" testId="chip-feed" />
      ) : (
        <ContextChip icon={WifiOff} label={th("pausedChip")} detail={th("pausedDetail", { api: API_BASE })} tone="review" testId="chip-feed" />
      ),
    },
  ];

  return (
    <AppShell
      sidebar={<Rail logo={<Logo variant="lockup" />} mark={<Logo variant="mark" />} items={nav} storageKey="evolve.rail.eval" />}
      topBar={
        <TopBar
          title={t("pageTitle")}
          mobileLogo={
            <span className="grid size-11 place-items-center rounded-md bg-navy">
              <Logo variant="mark" />
            </span>
          }
          actions={<LangSwitch href={`/${t("switchToLang")}`} label={t("switchTo")} lang={t("switchToLang")} compact />}
        />
      }
      contextStrip={<ContextStrip label={t("context")} items={chips} />}
      footer={<ShellFooter compliance={t("compliance")} environment={t("footerEnv")} />}
      theme="ledger"
    >
      {children}
    </AppShell>
  );
}
