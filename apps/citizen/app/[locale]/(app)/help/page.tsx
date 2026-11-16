"use client";
// Help (docs/09 §4.1-10): glossary, talk to a person (SIMULATED request), "Seven promises" (docs/03 §5),
// and "Who does what" (people · calculator · templates). Public: works without signing in.
import { Button } from "@evolve/ui/primitives/button";
import { Card, CardHeader, StatusChip } from "@evolve/ui/primitives/display";
import { SimulatedBadge } from "@evolve/ui/primitives/feedback";
import { Accordion } from "@evolve/ui/primitives/accordion";
import { useToast } from "@evolve/ui/primitives/toast";
import { SourceCaption } from "@evolve/ui/risk/risk";
import { PageHeader } from "@evolve/ui/shell/app-shell";
import { Calculator, FileText, PhoneCall, Users } from "lucide-react";
import { useTranslations } from "next-intl";

export default function HelpPage() {
  const t = useTranslations("help");
  const tc = useTranslations("chrome");
  const th = useTranslations("how");
  const toast = useToast();
  const terms = t.raw("terms") as Record<string, [string, string]>;
  const promises = t.raw("promiseItems") as [string, string][];
  const panels = [
    { k: "people", Icon: Users, cls: "bg-navy text-cream", sub: "text-mist", pill: "bg-lime text-navy" },
    { k: "calculator", Icon: Calculator, cls: "bg-accent-blue text-white", sub: "text-white", pill: "bg-white text-navy" },
    { k: "assistant", Icon: FileText, cls: "bg-accent-soft text-neutral-950", sub: "text-neutral-950/80", pill: "bg-navy text-cream" },
  ] as const;

  return (
    <>
      <PageHeader title={t("title")} description={t("description")} badge={<SimulatedBadge label={tc("simulated")} />} />
      <div className="grid gap-6 lg:grid-cols-12">
        <section aria-labelledby="glossary-h" className="space-y-3 lg:col-span-7">
          <h2 id="glossary-h" className="text-lg font-semibold">
            {t("glossary")}
          </h2>
          <Accordion items={Object.entries(terms).map(([k, [term, def]]) => ({ value: k, title: term, content: <p>{def}</p> }))} />
        </section>
        <Card id="contact" className="scroll-mt-24 lg:col-span-5" data-testid="contact">
          <CardHeader title={t("contact")} description={t("contactBody")} />
          <Button leadingIcon={<PhoneCall aria-hidden />} onClick={() => toast({ title: t("contactSim"), tone: "info" })}>
            {t("contactAction")}
          </Button>
        </Card>
      </div>

      <section aria-labelledby="promises-h" className="mt-10 space-y-3" data-testid="promises">
        <h2 id="promises-h" className="text-lg font-semibold">
          {t("promises")}
        </h2>
        <Card padding="none" className="overflow-hidden">
          <ol className="divide-y divide-line">
            {promises.map(([title, body], i) => (
              <li key={title} className="grid gap-2 px-5 py-4 sm:grid-cols-[2rem_1fr_auto] sm:items-center">
                <span className="font-mono text-sm text-ink-2">{String(i + 1).padStart(2, "0")}</span>
                <span>
                  <span className="block font-semibold">{title}</span>
                  <span className="block text-sm text-ink-2">{body}</span>
                </span>
                <StatusChip status="info" size="sm">
                  {t("promisesStatus")}
                </StatusChip>
              </li>
            ))}
          </ol>
        </Card>
      </section>

      <section aria-labelledby="who-h" className="mt-10 space-y-3">
        <h2 id="who-h" className="text-lg font-semibold">
          {t("who")}
        </h2>
        <ul className="grid gap-4 md:grid-cols-3" data-testid="three-panel">
          {panels.map(({ k, Icon, cls, sub, pill }) => (
            <li key={k} className={`flex flex-col gap-4 rounded-xl p-6 ${cls}`}>
              <Icon aria-hidden className="size-7" />
              <div>
                <h3 className="text-xl font-semibold">{th(`${k}.title`)}</h3>
                <p className={`mt-1 text-sm ${sub}`}>{th(`${k}.sub`)}</p>
              </div>
              <ul className="mt-auto space-y-2">
                {(["t1", "t2", "t3"] as const).map((x) => (
                  <li key={x} className="flex items-center justify-between gap-3 rounded-lg bg-black/10 px-4 py-3 text-sm">
                    <span>{th(`${k}.${x}`)}</span>
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${pill}`}>{th(`${k}.pill`)}</span>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
        <SourceCaption>{th("caption")}</SourceCaption>
      </section>
    </>
  );
}
