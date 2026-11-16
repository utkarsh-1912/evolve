"use client";
// Local UI preferences (no PHI): density and saved queue views, in localStorage.
import { useCallback, useSyncExternalStore } from "react";

export type Density = "comfortable" | "compact";
export interface QueueView {
  id: string;
  name: string;
  trigger: string; // "" = any
  status: string; // "" = any
  priority: string; // "" = any
  builtIn?: boolean;
}

const listeners = new Set<() => void>();
const subscribe = (cb: () => void) => {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
};
const emit = () => listeners.forEach((l) => l());

function useStored<T>(key: string, fallback: T): [T, (v: T) => void] {
  const raw = useSyncExternalStore(
    subscribe,
    () => window.localStorage.getItem(key),
    () => null,
  );
  let value = fallback;
  if (raw) {
    try {
      value = JSON.parse(raw) as T;
    } catch {
      value = fallback;
    }
  }
  const set = useCallback(
    (v: T) => {
      window.localStorage.setItem(key, JSON.stringify(v));
      emit();
    },
    [key],
  );
  return [value, set];
}

export const useDensity = () => useStored<Density>("evolve.counselor.density", "comfortable");
const NO_VIEWS: QueueView[] = [];
export const useSavedViews = () => useStored<QueueView[]>("evolve.counselor.views", NO_VIEWS);
