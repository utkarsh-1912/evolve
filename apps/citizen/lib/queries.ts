"use client";
// React Query wrappers around lib/api.ts (docs/09 §2). Every key is scoped by partner_id so cached data
// can never be served to a different signed-in partner (P-08); sign-out clears the cache.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { coupleIdFor, counterpartFor, setSession, useSession } from "./session";
import type { CompatibilityResponse, Session } from "./types";

export const qk = {
  vignettes: ["vignettes"] as const,
  vault: (pid: string) => ["me", pid, "vault"] as const,
  consents: (pid: string) => ["me", pid, "consents"] as const,
  messages: (pid: string) => ["me", pid, "messages"] as const,
  home: (pid: string) => ["me", pid, "home"] as const,
  activity: (pid: string) => ["me", pid, "activity"] as const,
  notifications: (pid: string) => ["me", pid, "notifications"] as const,
  carePlan: (pid: string) => ["me", pid, "care-plan"] as const,
  loop: (pid: string) => ["me", pid, "loop"] as const,
  compat: (pid: string) => ["me", pid, "compat-result"] as const,
  teachback: (pid: string) => ["me", pid, "teachback"] as const,
};

function useMe() {
  const { session, ready } = useSession();
  return { session, ready, token: session?.token ?? null, pid: session?.partner_id ?? "" };
}

export const useVignettes = () => useQuery({ queryKey: qk.vignettes, queryFn: () => api.vignettes(), staleTime: Infinity });

export function useVault() {
  const { token, pid } = useMe();
  return useQuery({ queryKey: qk.vault(pid), queryFn: () => api.vault(token), enabled: !!token });
}
export function useConsents() {
  const { token, pid } = useMe();
  return useQuery({ queryKey: qk.consents(pid), queryFn: () => api.listConsents(token), enabled: !!token });
}
export function useHome() {
  const { token, pid } = useMe();
  return useQuery({ queryKey: qk.home(pid), queryFn: () => api.home(token), enabled: !!token });
}
export function useActivity(limit = 20) {
  const { token, pid } = useMe();
  return useQuery({ queryKey: [...qk.activity(pid), limit], queryFn: () => api.activity(token, limit), enabled: !!token });
}
export function useNotifications() {
  const { token, pid } = useMe();
  return useQuery({ queryKey: qk.notifications(pid), queryFn: () => api.notifications(token), enabled: !!token });
}
export function useCarePlan() {
  const { token, pid } = useMe();
  return useQuery({ queryKey: qk.carePlan(pid), queryFn: () => api.carePlan(token), enabled: !!token });
}
export function useLoop() {
  const { token, pid } = useMe();
  return useQuery({ queryKey: qk.loop(pid), queryFn: () => api.loop(token, coupleIdFor(pid)), enabled: !!token });
}

/** Invalidate everything that depends on consent / couple / loop state for the current partner. */
function useInvalidateCouple() {
  const qc = useQueryClient();
  const { pid } = useMe();
  return () =>
    Promise.all(
      [qk.consents(pid), qk.home(pid), qk.activity(pid), qk.messages(pid), qk.vault(pid), qk.carePlan(pid), qk.notifications(pid), qk.loop(pid)].map(
        (queryKey) => qc.invalidateQueries({ queryKey }),
      ),
    );
}

export function useMessages() {
  const { token, pid } = useMe();
  return useQuery({ queryKey: qk.messages(pid), queryFn: () => api.messages(token), enabled: !!token });
}

/** The last compatibility result this session (kept in the query cache so navigation does not lose it). */
export function useCompatResult() {
  const { pid } = useMe();
  return useQuery<CompatibilityResponse | null>({ queryKey: qk.compat(pid), queryFn: () => null, enabled: false, initialData: null, staleTime: Infinity });
}

export function useSignIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ partnerId, lang }: { partnerId: string; lang: "en" | "ar" }) => api.createSession(partnerId, lang),
    onSuccess: (s: Session) => {
      qc.clear();
      setSession(s);
    },
  });
}
export function useSignOut() {
  const qc = useQueryClient();
  return () => {
    qc.clear();
    setSession(null);
  };
}

export function useGrantConsent() {
  const { token, pid } = useMe();
  const inv = useInvalidateCouple();
  return useMutation({ mutationFn: () => api.grantConsent(token, counterpartFor(pid)), onSuccess: inv });
}
export function useRevokeConsent() {
  const { token } = useMe();
  const inv = useInvalidateCouple();
  const clear = useClearCompatResult();
  return useMutation({
    mutationFn: (id: string) => api.revokeConsent(token, id),
    onSuccess: () => {
      clear();
      return inv();
    },
  });
}
export function useSimulatePartnerConsent() {
  const { pid } = useMe();
  const inv = useInvalidateCouple();
  return useMutation({ mutationFn: () => api.simulatePartnerConsent(coupleIdFor(pid)), onSuccess: inv });
}
export function useCompatibility() {
  const { token, pid } = useMe();
  const qc = useQueryClient();
  const inv = useInvalidateCouple();
  return useMutation({
    mutationFn: () => api.compatibility(token, coupleIdFor(pid)),
    onSuccess: (data) => {
      qc.setQueryData(qk.compat(pid), data);
      return inv();
    },
  });
}
export function useClearCompatResult() {
  const { pid } = useMe();
  const qc = useQueryClient();
  return () => qc.setQueryData(qk.compat(pid), null);
}

export function useTeachbackStart() {
  const { token, pid } = useMe();
  return useQuery({ queryKey: qk.teachback(pid), queryFn: () => api.teachbackStart(token), enabled: !!token, staleTime: Infinity });
}
export function useSubmitTeachback() {
  const { token } = useMe();
  const inv = useInvalidateCouple();
  return useMutation({ mutationFn: (answers: boolean[]) => api.submitTeachback(token, answers), onSuccess: () => inv() });
}
export function useSubmitSure() {
  const { token } = useMe();
  const inv = useInvalidateCouple();
  return useMutation({ mutationFn: (answers: boolean[]) => api.submitSure(token, answers), onSuccess: () => inv() });
}
export function useFamilyToken() {
  const { token } = useMe();
  return useMutation({ mutationFn: (hgnc_id: number) => api.familyToken(token, hgnc_id) });
}
export function useMarkAllNotificationsRead() {
  const { token, pid } = useMe();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (ids: string[]) => Promise.all(ids.map((id) => api.markNotificationRead(token, id))),
    onSuccess: () => Promise.all([qk.notifications(pid), qk.home(pid)].map((queryKey) => qc.invalidateQueries({ queryKey }))),
  });
}
