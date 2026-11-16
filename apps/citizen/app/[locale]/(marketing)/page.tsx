import { ChamferCTA } from "@evolve/ui/primitives/button";
import { OverlapCircles } from "@evolve/ui/risk/motion";
import { useTranslations } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { use } from "react";
import { Link } from "@/i18n/navigation";

// Marketing landing (un-shelled): hero + Venn, one chamfered CTA, "TWO [overlap] CIRCLES", "How we protect you".
export default function Landing({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = use(params);
  setRequestLocale(locale);
  const t = useTranslations("landing");
  const nav = useTranslations("chrome.nav");
  const rows = [
    ["privateTitle", "privateBody"],
    ["numbersTitle", "numbersBody"],
    ["peopleTitle", "peopleBody"],
    ["decideTitle", "decideBody"],
  ] as const;

  return (
    <div className="space-y-16">
      <section className="relative overflow-hidden rounded-xl bg-navy p-6 text-cream sm:p-12" aria-labelledby="hero-title">
        <div aria-hidden className="halftone pointer-events-none absolute inset-0" />
        <div className="relative grid items-center gap-8 lg:grid-cols-[1.4fr_1fr]">
          <div className="space-y-6">
            <p className="text-sm font-semibold uppercase tracking-[0.08em] text-mist">{t("eyebrow")}</p>
            <h1 id="hero-title" className="font-display text-[clamp(2.25rem,6vw,4.5rem)] font-medium leading-[1.05] text-cream">
              {t("headline")}
            </h1>
            <p className="max-w-[60ch] text-lg text-cream/90">{t("lede")}</p>
            <div className="flex flex-wrap items-center gap-4">
              <ChamferCTA href="/sign-in">{nav("cta")}</ChamferCTA>
              <Link href="/help" className="inline-flex min-h-11 items-center rounded-md border border-cream/50 px-5 text-cream underline-offset-4 hover:underline">
                {t("secondary")}
              </Link>
            </div>
          </div>
          <div className="flex justify-center">
            <OverlapCircles phase="idle" label={t("venn")} onDark />
          </div>
        </div>
      </section>

      <section aria-labelledby="two-circles" className="space-y-4 text-center">
        <h2 id="two-circles" className="flex flex-wrap items-center justify-center gap-x-4 font-display text-[clamp(2.5rem,10vw,6rem)] font-semibold uppercase leading-none text-navy">
          <span>{t("twoCirclesA")}</span>
          <span className="inline-block w-[clamp(5rem,16vw,9rem)]">
            <OverlapCircles phase="idle" label="" size={160} decorative />
          </span>
          <span>{t("twoCirclesB")}</span>
        </h2>
        <p className="mx-auto max-w-2xl text-lg text-ink-2">{t("twoCirclesBody")}</p>
      </section>

      <section aria-labelledby="protect" className="grid gap-6 rounded-xl bg-neutral-950 p-6 text-neutral-50 sm:p-10 lg:grid-cols-[1fr_3fr]">
        <h2 id="protect" className="text-sm font-semibold uppercase tracking-[0.08em] text-lime">
          {t("protectLabel")}
        </h2>
        <ul className="divide-y divide-white/15">
          {rows.map(([title, body]) => (
            <li key={title} className="grid gap-2 py-5 sm:grid-cols-[1fr_1.5fr]">
              <h3 className="text-2xl font-light">{t(`protect.${title}`)}</h3>
              <p className="text-neutral-50/85">{t(`protect.${body}`)}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
