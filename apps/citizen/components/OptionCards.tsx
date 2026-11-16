import { Card } from "@evolve/ui/primitives/display";
import { useTranslations } from "next-intl";

// Non-directive option cards (P-13): identical visual weight, no default selection, no "recommended" badge.
export function OptionCards() {
  const t = useTranslations("options");
  const items = [
    { k: "counsel", title: t("counselTitle"), body: t("counselBody") },
    { k: "learn", title: t("learnTitle"), body: t("learnBody") },
    { k: "questions", title: t("questionsTitle"), body: t("questionsBody") },
  ];
  return (
    <section aria-labelledby="options-title" className="space-y-3">
      <h2 id="options-title" className="text-lg font-semibold">
        {t("title")}
      </h2>
      <p className="text-sm text-ink-2">{t("note")}</p>
      <ul className="grid gap-3 sm:grid-cols-3" data-testid="option-cards">
        {items.map((i) => (
          <Card as="li" key={i.k} padding="sm" className="p-5">
            <h3 className="font-semibold">{i.title}</h3>
            <p className="mt-2 text-sm text-ink-2">{i.body}</p>
          </Card>
        ))}
      </ul>
    </section>
  );
}
