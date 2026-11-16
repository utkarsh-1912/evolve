"use client";
// Global search: case ID only (docs/09 §3). No gene or person search across patients. Exact or unique-prefix match
// against the case list the counselor can already see on shift.
import { Input, useToast } from "@evolve/ui";
import { Search } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useId, useState } from "react";
import { useRouter } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { cn } from "@evolve/ui";

export function CaseSearch({ className, testId = "case-search" }: { className?: string; testId?: string }) {
  const t = useTranslations("chrome.search");
  const { session } = useSession();
  const qc = useQueryClient();
  const router = useRouter();
  const toast = useToast();
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const id = useId();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const needle = q.trim().toLowerCase();
    if (!needle || !session) return;
    if (!session.on_shift) {
      setError(t("offShift"));
      return;
    }
    try {
      const rows = await qc.fetchQuery({ queryKey: ["cases", session.token, "", ""], queryFn: () => api.cases(session.token, {}) });
      const exact = rows.find((r) => r.case_id.toLowerCase() === needle);
      const prefix = rows.filter((r) => r.case_id.toLowerCase().startsWith(needle));
      const hit = exact ?? (prefix.length === 1 ? prefix[0] : undefined);
      if (!hit) {
        setError(t("notFound"));
        return;
      }
      setError(null);
      setQ("");
      router.push(`/cases/${encodeURIComponent(hit.case_id)}`);
    } catch {
      toast({ title: t("notFound"), tone: "danger" });
    }
  };

  return (
    <form role="search" onSubmit={submit} className={cn("relative", className)} data-testid={testId}>
      <label htmlFor={id} className="sr-only">
        {t("label")}
      </label>
      <div className="relative">
        <Search aria-hidden className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-ink-2" />
        <Input
          id={id}
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setError(null);
          }}
          placeholder={t("placeholder")}
          autoComplete="off"
          spellCheck={false}
          dir="ltr"
          aria-describedby={`${id}-help ${id}-err`}
          aria-invalid={error ? true : undefined}
          className="w-56 ps-9 font-mono text-sm"
        />
      </div>
      <p id={`${id}-help`} className="sr-only">
        {t("help")}
      </p>
      <p id={`${id}-err`} role="alert" className={cn("text-xs font-medium text-escalated-ink", error ? "absolute top-full mt-1 whitespace-nowrap rounded-sm bg-surface-3 px-2 py-1 shadow-e2" : "sr-only")}>
        {error ?? ""}
      </p>
      <button type="submit" className="sr-only">
        {t("submit")}
      </button>
    </form>
  );
}
