// Five metric panels (docs/00 success metrics, R-EVAL-1). Every value, CI, target and verdict is read from
// the evidence pack; the pack's own `meets` flag is shown, never recomputed. Simulated dimensions are stamped.
import { Accordion, Card, Notice } from "@evolve/ui";
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { evidence } from "@/lib/evidence";
import { count, pct, pctTarget } from "@/lib/format";
import { KV, ShareValue, Verdict } from "./bits";

function Panel({
  id,
  title,
  basis,
  simulated,
  meets,
  primaryLabel,
  primary,
  target,
  children,
}: {
  id: string;
  title: string;
  basis: string;
  simulated: boolean;
  meets: boolean;
  primaryLabel: string;
  primary: ReactNode;
  target: string;
  children?: ReactNode;
}) {
  const t = useTranslations("dim");
  return (
    <Card as="article" variant="raised" className="flex flex-col gap-5" aria-labelledby={`${id}-t`} data-testid={`dim-${id}`}>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <h3 id={`${id}-t`} className="font-display text-xl font-semibold text-ink">
          {title}
        </h3>
        <div className="flex flex-wrap items-center gap-2" data-simulated-dimension={simulated}>
          <Verdict meets={meets} testId={`verdict-${id}`} />
        </div>
      </header>
      <p className="text-sm text-ink-2">
        <span className="font-semibold text-ink">{t("basis")}:</span> {basis}
      </p>
      <div>
        <p className="mb-2 text-sm font-semibold text-ink">{primaryLabel}</p>
        {primary}
        <p className="mt-2 text-sm text-ink-2">
          {t("target")}: <span className="font-mono font-semibold text-ink" dir="ltr">{target}</span>
        </p>
      </div>
      {children ? <div className="mt-auto">{children}</div> : null}
    </Card>
  );
}

export function MetricPanels() {
  const t = useTranslations("dim");
  const locale = useLocale();
  const d = evidence.dimensions;
  const th = evidence.thresholds;
  const c = d.comprehension;
  const ic = d.informed_choice;
  const lv = d.loop_velocity;
  const cal = d.calibration;
  const pr = d.privacy;
  const det = evidence.calibration_detail;

  const strata = Object.keys(c.by_stratum).sort();

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2 2xl:grid-cols-3">
        <Panel
          id="comprehension"
          title={t("comprehension.title")}
          basis={t("comprehension.basis")}
          simulated={c.simulated}
          meets={c.meets}
          primaryLabel={t("comprehension.primary")}
          primary={<ShareValue share={c.first_attempt_pass} testId="value-comprehension" />}
          target={`≥ ${pctTarget(th.comprehension_share, locale)}`}
        >
          <KV k={t("comprehension.final")} v={<span dir="ltr">{pct(c.final_pass.value, locale)} ({t("kn", { k: c.final_pass.k, n: c.final_pass.n })})</span>} />
          <div className="border-t border-line py-2" data-testid="gcos">
            <dl className="flex flex-wrap items-baseline justify-between gap-x-4">
              <dt className="text-sm text-ink-2">{t("comprehension.gcos")}</dt>
              <dd className="text-sm font-semibold text-review-ink">
                {c.gcos.instrumented ? String(c.gcos.p_value) : t("comprehension.gcosValue")}
                <span className="ms-2 font-mono font-normal text-ink-2" dir="ltr">
                  ({t("target")} p &lt; {th.gcos_p_value_below})
                </span>
              </dd>
            </dl>
            {!c.gcos.instrumented ? <p className="mt-1 text-xs text-ink-2">{t("comprehension.gcosNote")}</p> : null}
          </div>
          <p className="border-t border-line pt-2 text-sm font-semibold text-ink">{t("comprehension.items")}</p>
          {Object.entries(c.per_item).map(([key, s]) => (
            <KV key={key} k={t(`comprehension.item.${key}` as "comprehension.item.you_decide")} v={<span dir="ltr">{pct(s.value, locale)}</span>} />
          ))}
        </Panel>

        <Panel
          id="informed_choice"
          title={t("informed_choice.title")}
          basis={t("informed_choice.basis")}
          simulated={ic.simulated}
          meets={ic.meets}
          primaryLabel={t("informed_choice.primary")}
          primary={<ShareValue share={ic.sure_full} testId="value-sure" />}
          target={`≥ ${pctTarget(th.sure_full_share, locale)}`}
        >
          <KV
            k={t("informed_choice.coercion")}
            v={
              <span dir="ltr">
                {count(ic.coercion_flags, locale)} <span className="font-normal text-ink-2">({t("target")} {count(th.coercion_flags_max, locale)})</span>
              </span>
            }
          />
        </Panel>

        <Panel
          id="loop_velocity"
          title={t("loop_velocity.title")}
          basis={t("loop_velocity.basis")}
          simulated={lv.simulated}
          meets={lv.meets}
          primaryLabel={t("loop_velocity.primary")}
          primary={<ShareValue share={lv.booked_within_48h} testId="value-booked" />}
          target={pctTarget(th.booked_within_48h_share, locale)}
        >
          <KV
            k={t("loop_velocity.confirmatory")}
            v={
              <span dir="ltr">
                {pct(lv.confirmatory_completed.value, locale)} ({t("kn", { k: lv.confirmatory_completed.k, n: lv.confirmatory_completed.n })}){" "}
                <span className="font-normal text-ink-2">
                  {t("target")} ≥ {pctTarget(th.confirmatory_completed_share, locale)}
                </span>
              </span>
            }
          />
          <KV k={t("loop_velocity.late")} v={count(lv.late_or_unbooked.length, locale)} />
        </Panel>

        <Panel
          id="calibration"
          title={t("calibration.title")}
          basis={t("calibration.basis")}
          simulated={cal.simulated}
          meets={cal.meets}
          primaryLabel={t("calibration.primary")}
          primary={
            <div data-testid="value-calibration">
              <p className="font-display text-5xl font-light leading-none tracking-tight text-ink xl:text-6xl" dir="ltr">
                {count(cal.arithmetic_mismatches, locale)}
              </p>
              <p className="mt-2 font-mono text-sm text-ink-2">{t("calibration.of", { n: count(cal.records_checked, locale), numeric: count(det.numeric_records, locale) })}</p>
            </div>
          }
          target={count(th.arithmetic_mismatches_max, locale)}
        >
          <KV
            k={t("calibration.fhir")}
            v={
              <span>
                {count(cal.fhir_errors, locale)}{" "}
                <span className="font-normal text-ink-2">
                  {t("calibration.fhirOf", { resources: count(det.fhir_counts.resources ?? 0, locale), couples: count(det.fhir_counts.couples ?? 0, locale) })}
                </span>
              </span>
            }
          />
        </Panel>

        <Panel
          id="privacy"
          title={t("privacy.title")}
          basis={t("privacy.basis")}
          simulated={pr.simulated}
          meets={pr.meets}
          primaryLabel={t("privacy.primary")}
          primary={<ShareValue share={pr.interception} testId="value-interception" />}
          target={pctTarget(th.interception_share, locale)}
        >
          <KV
            k={t("privacy.redteamLeaks")}
            v={
              <span className="text-escalated-ink" data-testid="redteam-leaks">
                {count(pr.redteam_leaks, locale)} <span className="font-normal text-ink-2">({t("target")} {count(th.leaks_max, locale)})</span>
              </span>
            }
          />
          <KV
            k={t("privacy.live")}
            v={
              <span>
                {count(pr.live_leaks, locale)} <span className="font-normal text-ink-2">{t("privacy.liveOf", { n: count(pr.live_responses_scanned, locale) })}</span>
              </span>
            }
          />
        </Panel>

        <Notice className="self-start text-sm">{t("artifactNote")}</Notice>
      </div>

      <Accordion
        items={[
          {
            value: "strata",
            title: t("strata"),
            content: (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <caption className="sr-only">{t("strata")}</caption>
                  <thead>
                    <tr className="border-b border-line text-start text-ink-2">
                      <th scope="col" className="py-2 pe-4 text-start font-semibold">
                        {t("stratum")}
                      </th>
                      <th scope="col" className="py-2 pe-4 text-start font-semibold">
                        {t("comprehension.primary")}
                      </th>
                      <th scope="col" className="py-2 text-start font-semibold">
                        {t("informed_choice.primary")}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {strata.map((s) => {
                      const a = c.by_stratum[s];
                      const b = ic.by_stratum[s];
                      return (
                        <tr key={s} className="border-b border-line last:border-b-0">
                          <th scope="row" className="py-1.5 pe-4 text-start font-mono font-normal text-ink">
                            {s}
                          </th>
                          <td className="py-1.5 pe-4 font-mono" dir="ltr">
                            {pct(a.value, locale)} ({t("kn", { k: a.k, n: a.n })})
                          </td>
                          <td className="py-1.5 font-mono" dir="ltr">
                            {b ? `${pct(b.value, locale)} (${t("kn", { k: b.k, n: b.n })})` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
