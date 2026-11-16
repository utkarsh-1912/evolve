"use client";
// SIMULATED counselor sign-in (api.md: POST /api/session {role:"counselor"}). Shift starts OFF (DECISIONS #40).
import { Alert, Button, Card, FormField, LangSwitch, Notice, PageHeader, Select, ShellFooter, SimulatedBadge } from "@evolve/ui";
import { Clock } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { usePathname, useRouter } from "@/i18n/navigation";
import { useSignIn } from "@/lib/queries";
import { BrandLogo } from "./BrandLogo";

const ACCOUNTS = ["counselor-1", "counselor-2"];

export function SignInScreen() {
  const t = useTranslations("signIn");
  const tc = useTranslations("chrome");
  const router = useRouter();
  const pathname = usePathname();
  const signIn = useSignIn();
  const [who, setWho] = useState(ACCOUNTS[0]);
  const other = tc("lang.switchToLang");
  return (
    <div data-theme="ledger" className="flex min-h-dvh flex-col bg-surface-0 text-ink">
      <header className="flex items-center justify-between bg-navy px-4 py-3 md:px-8">
        <BrandLogo height={32} href="/sign-in" />
        <span className="rounded-md bg-surface-0">
          <LangSwitch href={`/${other}${pathname}`} label={tc("lang.switchTo")} lang={other} />
        </span>
      </header>
      <main id="main" className="mx-auto w-full max-w-xl flex-1 px-4 py-10">
        <PageHeader title={t("title")} description={t("description")} badge={<SimulatedBadge label={tc("simulated")} />} />
        <Card>
          <form
            className="space-y-5"
            onSubmit={(e) => {
              e.preventDefault();
              signIn.mutate(who, { onSuccess: () => router.push("/queue") });
            }}
          >
            <FormField label={t("counselor")}>
              <Select value={who} onValueChange={setWho} options={ACCOUNTS.map((a) => ({ value: a, label: a }))} />
            </FormField>
            <Notice icon={Clock}>{t("shiftNote")}</Notice>
            {signIn.isError ? <Alert tone="danger">{t("error")}</Alert> : null}
            <Button type="submit" size="lg" block loading={signIn.isPending} data-testid="sign-in">
              {t("submit")}
            </Button>
          </form>
        </Card>
      </main>
      <ShellFooter compliance={tc("compliance")} environment={tc("footerEnv")} />
    </div>
  );
}
