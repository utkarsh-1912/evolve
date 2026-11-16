"use client";
import { Button } from "@evolve/ui/primitives/button";
import { LangSwitch } from "@evolve/ui/shell/lang-switch";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { BrandLogo } from "./BrandLogo";

// Header for un-shelled routes (marketing landing, sign-in, design system): logo, language, one action.
export function SimpleHeader({ showSignIn = true }: { showSignIn?: boolean }) {
  const t = useTranslations("chrome");
  const pathname = usePathname();
  const other = t("lang.switchToLang");
  return (
    <header className="bg-navy text-cream">
      <div className="mx-auto flex max-w-[var(--content-max)] items-center gap-3 px-4 py-4 md:px-8">
        <BrandLogo height={36} descriptor={t("brandDescriptor")} />
        <div className="ms-auto flex items-center gap-2 [&_a[data-testid=lang-switch]]:text-cream [&_a[data-testid=lang-switch]:hover]:bg-white/10">
          <LangSwitch href={`/${other}${pathname === "/" ? "" : pathname}`} label={t("lang.switchTo")} lang={other} />
          {showSignIn ? (
            <Button asChild variant="lime" size="sm">
              <Link href="/sign-in">{t("signIn")}</Link>
            </Button>
          ) : null}
        </div>
      </div>
    </header>
  );
}

export function SimpleFooter() {
  const t = useTranslations("chrome");
  return (
    <footer className="border-t border-line bg-surface-1 px-4 py-4 text-sm md:px-8" data-testid="shell-footer">
      <div className="mx-auto flex max-w-[var(--content-max)] flex-col gap-1 md:flex-row md:justify-between">
        <p className="font-medium text-ink" data-testid="compliance-line">
          {t("compliance")}
        </p>
        <p className="text-ink-2">{t("footerEnv")}</p>
      </div>
    </footer>
  );
}
