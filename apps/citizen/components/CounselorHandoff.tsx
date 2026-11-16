import { UserRoundCheck } from "lucide-react";
import { useTranslations } from "next-intl";

// P-18 escalation: hand off to a human genetic counselor (CounselorCopilot triggers live in the backend).
export function CounselorHandoff() {
  const t = useTranslations("handoff");
  return (
    <section data-testid="counselor-handoff" className="rounded-xl bg-navy p-6 text-cream" aria-labelledby="handoff-title">
      <div className="flex flex-wrap items-center gap-2">
        <UserRoundCheck aria-hidden className="size-5 text-lime" />
        <span className="text-sm font-semibold text-lime">{t("label")}</span>
      </div>
      <h2 id="handoff-title" className="mt-3 text-xl font-semibold">
        {t("title")}
      </h2>
      <p className="mt-2 max-w-[72ch] text-cream/90">{t("body")}</p>
      <p className="mt-3 text-sm text-mist">{t("booking")} · {t("simulated")}</p>
    </section>
  );
}
