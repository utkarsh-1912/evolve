"use client";
// Per-user session (P-08): one partner per browser tab, kept in sessionStorage only.
// Signing in as another partner replaces the session and clears every cached query (lib/query-client.ts).
import { useSyncExternalStore } from "react";
import type { Session } from "./types";

const KEY = "evolve.session.v1";
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

let cachedRaw: string | null = null;
let cached: Session | null = null;

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(KEY);
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cached = raw ? (JSON.parse(raw) as Session) : null;
  }
  return cached;
}

export function setSession(s: Session | null) {
  if (s) window.sessionStorage.setItem(KEY, JSON.stringify(s));
  else window.sessionStorage.removeItem(KEY);
  emit();
}

export function useSession(): { session: Session | null; ready: boolean } {
  const session = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    getSession,
    () => null,
  );
  const ready = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  return { session, ready };
}

/** Couple id for a synthetic partner id (V1A -> V1). Used only to address API routes. */
export const coupleIdFor = (partnerId: string) => partnerId.replace(/[AB]$/, "");
export const counterpartFor = (partnerId: string) =>
  partnerId.endsWith("A") ? partnerId.replace(/A$/, "B") : partnerId.replace(/B$/, "A");
