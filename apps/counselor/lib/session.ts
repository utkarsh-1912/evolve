"use client";
// Counselor session (SIMULATED sign-in), kept in sessionStorage only. Shift starts OFF (DECISIONS #40 (4)).
import { useSyncExternalStore } from "react";
import type { CounselorSession } from "./types";

const KEY = "evolve.counselor.session.v1";
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

let cachedRaw: string | null = null;
let cached: CounselorSession | null = null;

export function getSession(): CounselorSession | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(KEY);
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cached = raw ? (JSON.parse(raw) as CounselorSession) : null;
  }
  return cached;
}

export function setSession(s: CounselorSession | null) {
  if (s) window.sessionStorage.setItem(KEY, JSON.stringify(s));
  else window.sessionStorage.removeItem(KEY);
  emit();
}

const subscribe = (cb: () => void) => {
  listeners.add(cb);
  return () => listeners.delete(cb);
};

export function useSession(): { session: CounselorSession | null; ready: boolean } {
  const session = useSyncExternalStore(subscribe, getSession, () => null);
  const ready = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  return { session, ready };
}
