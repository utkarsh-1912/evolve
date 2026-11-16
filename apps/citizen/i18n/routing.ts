import { defineRouting } from "next-intl/routing";

// R-UX-1: bilingual citizen app. AR is a scaffold (strings TODO(ar)), but RTL layout is live.
export const routing = defineRouting({
  locales: ["en", "ar"],
  defaultLocale: "en",
  localePrefix: "always",
});

export type Locale = (typeof routing.locales)[number];
export const dirFor = (locale: string) => (locale === "ar" ? "rtl" : "ltr");
