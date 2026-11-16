"use client";
import { useLocale } from "next-intl";
import { useSyncExternalStore } from "react";

/** Date/time formatting (Latin digits in AR to match IDs and locked figures). */
export function useFormatTs() {
  const locale = useLocale();
  return (iso: string) =>
    new Intl.DateTimeFormat(locale === "ar" ? "ar-AE-u-nu-latn" : "en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
}

// One shared 30 s clock for every SLA timer.
let tick = typeof window === "undefined" ? 0 : Date.now();
const clockListeners = new Set<() => void>();
let clockId: number | null = null;
function subscribeClock(cb: () => void) {
  clockListeners.add(cb);
  if (clockId === null) {
    tick = Date.now();
    clockId = window.setInterval(() => {
      tick = Date.now();
      clockListeners.forEach((l) => l());
    }, 30_000);
  }
  return () => {
    clockListeners.delete(cb);
    if (!clockListeners.size && clockId !== null) {
      window.clearInterval(clockId);
      clockId = null;
    }
  };
}

/** Current time (ms), refreshed every 30 s. Null during SSR so server and client markup match. */
export function useNow(): number | null {
  return useSyncExternalStore(
    subscribeClock,
    () => tick,
    () => null,
  );
}

/** "V2A" from "Patient/V2A". */
export const patientId = (ref: string) => ref.replace(/^Patient\//, "");
