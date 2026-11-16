"use client";
// React Query wrappers. Keys are scoped by the counselor session token; every mutation invalidates the case data.
// Off shift, no case query runs at all (the UI shows the permission-denied state; the backend also returns 403).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type CaseFilters } from "./api";
import { setSession, useSession } from "./session";
import type { LoopState, TaskKind, TaskStatus } from "./types";

export function useCases(filters: CaseFilters = {}) {
  const { session } = useSession();
  return useQuery({
    queryKey: ["cases", session?.token, filters.status ?? "", filters.trigger ?? ""],
    queryFn: () => api.cases(session!.token, filters),
    enabled: !!session?.on_shift,
  });
}

export function useCaseView(caseId: string) {
  const { session } = useSession();
  return useQuery({
    queryKey: ["case", session?.token, caseId],
    queryFn: () => api.caseView(session!.token, caseId),
    enabled: !!session?.on_shift,
  });
}

export function useSignIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (counselorId: string) => api.createSession(counselorId),
    onSuccess: (s) => {
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

export function useShift() {
  const { session } = useSession();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (on: boolean) => api.setShift(session!.token, on),
    onSuccess: (r) => {
      if (session) setSession({ ...session, on_shift: r.on_shift });
      if (!r.on_shift) qc.removeQueries({ queryKey: ["case"] });
      qc.invalidateQueries();
    },
  });
}

function useCaseMutation<V>(fn: (token: string, v: V) => Promise<unknown>) {
  const { session } = useSession();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: V) => fn(session!.token, v),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["case"] });
      qc.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}

export const useAdvanceLoop = () => useCaseMutation((t, v: { coupleId: string; to: LoopState }) => api.advanceLoop(t, v.coupleId, v.to));
export const useCreateTask = () =>
  useCaseMutation((t, v: { caseId: string; kind: TaskKind; hgnc_id?: number }) => api.createTask(t, v.caseId, { kind: v.kind, hgnc_id: v.hgnc_id }));
export const useUpdateTask = () =>
  useCaseMutation((t, v: { caseId: string; taskId: string; status: TaskStatus }) => api.updateTask(t, v.caseId, v.taskId, v.status));
export const useAddNote = () => useCaseMutation((t, v: { caseId: string; text: string }) => api.addNote(t, v.caseId, v.text));
export const useClosure = () => useCaseMutation((t, v: { caseId: string; summary: string }) => api.closure(t, v.caseId, v.summary));

// v1.3.0 (DECISIONS #62): AI draft availability and the counselor-only summary draft (never cached on the case).
export function useConfig() {
  return useQuery({ queryKey: ["config"], queryFn: () => api.config(), staleTime: 5 * 60_000 });
}

export function useSummaryDraft() {
  const { session } = useSession();
  return useMutation({ mutationFn: (caseId: string) => api.summaryDraft(session!.token, caseId) });
}
