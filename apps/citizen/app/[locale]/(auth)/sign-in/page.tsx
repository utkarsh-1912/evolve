"use client";
import { Avatar, Card } from "@evolve/ui/primitives/display";
import { ErrorState, LoadingRegion, SimulatedBadge, Skeleton } from "@evolve/ui/primitives/feedback";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { ChevronRight } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { useSignIn, useVignettes } from "@/lib/queries";

// SIMULATED sign-in picker (contracts/api.md: POST /api/session). Synthetic V1–V5 partners only.
export default function SignIn() {
  const t = useTranslations("signIn");
  const tc = useTranslations("chrome");
  const router = useRouter();
  const locale = useLocale();
  const vignettes = useVignettes();
  const signIn = useSignIn();

  return (
    <div>
      <PageHeader title={t("title")} description={t("body")} badge={<SimulatedBadge label={tc("simulated")} />} />
      {vignettes.isError ? <ErrorState onRetry={() => vignettes.refetch()} reference="SIGNIN-VIGNETTES" /> : null}
      {signIn.isError ? <ErrorState reference="SIGNIN-SESSION" /> : null}
      {vignettes.isLoading ? (
        <LoadingRegion>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 5 }, (_, i) => (
              <li key={i}>
                <Skeleton className="h-44" rounded="lg" />
              </li>
            ))}
          </ul>
        </LoadingRegion>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {vignettes.data?.map((v) => (
            <Card as="li" key={v.couple_id}>
              <h2 className="text-sm font-semibold text-ink-2">{v.label}</h2>
              <div className="mt-4 grid gap-2">
                {v.partner_ids.map((pid, i) => (
                  <button
                    key={pid}
                    type="button"
                    data-testid={`signin-${pid}`}
                    disabled={signIn.isPending}
                    onClick={() => signIn.mutate({ partnerId: pid, lang: locale === "ar" ? "ar" : "en" }, { onSuccess: () => router.push("/home") })}
                    className="flex min-h-14 items-center gap-3 rounded-lg border border-line bg-surface-2 px-3 text-start transition-colors hover:border-navy disabled:opacity-60"
                  >
                    <Avatar name={pid} size="sm" />
                    <span className="flex-1">
                      <span className="block font-semibold text-ink">{t("partner", { role: i === 0 ? "A" : "B" })}</span>
                      <span className="block text-sm text-ink-2">
                        {signIn.isPending && signIn.variables?.partnerId === pid ? t("working") : t("signInAs", { id: pid })}
                      </span>
                    </span>
                    <ChevronRight aria-hidden className="size-5 text-ink-2 rtl:-scale-x-100" />
                  </button>
                ))}
              </div>
            </Card>
          ))}
        </ul>
      )}
    </div>
  );
}
