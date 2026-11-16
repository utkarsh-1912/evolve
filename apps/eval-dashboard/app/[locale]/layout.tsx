import type { Metadata, Viewport } from "next";
import { notFound } from "next/navigation";
import { hasLocale, NextIntlClientProvider } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { EnvironmentBanner } from "@evolve/ui";
import { dirFor, routing } from "@/i18n/routing";
import { instrument, jetbrains, lexend, plexArabic } from "../fonts";
import { Providers } from "@/components/Providers";
import "../globals.css";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "meta" });
  return { title: t("title"), description: t("description"), robots: { index: false } };
}

export const viewport: Viewport = { themeColor: "#141412", width: "device-width", initialScale: 1 };

// Eval dashboard (R-EVAL-1): Ledger theme (docs/03 §3), the ONE global SIMULATED environment banner (A7, P-19).
export default async function LocaleLayout({ children, params }: { children: React.ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "chrome" });
  const dir = dirFor(locale) as "ltr" | "rtl";
  return (
    <html lang={locale} dir={dir} data-theme="ledger" className={`${lexend.variable} ${instrument.variable} ${jetbrains.variable} ${plexArabic.variable}`}>
      <body className="grain min-h-dvh bg-surface-0 text-ink antialiased">
        <NextIntlClientProvider>
          <Providers dir={dir}>
            <EnvironmentBanner label={t("envLabel")} detail={t("envDetail")} />
            {locale === "ar" ? (
              <p className="bg-review/20 px-4 py-2 text-center text-sm text-ink" data-testid="ar-pending">
                {t("arPending")}
              </p>
            ) : null}
            {children}
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
