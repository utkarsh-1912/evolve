// Typed client for the two live endpoints the dashboard uses (contracts/api.md v1.2.1).
// There is no mock adapter here: if the backend is down, the UI says so (no simulated "live" data).

export const API_BASE = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

export type GateRule =
  | "numeric_drift"
  | "leakage"
  | "directive"
  | "uae_law"
  | "missing_judicial_statement"
  | "stigma"
  | "false_reassurance"
  | "gate_error";

/** GET /api/guardrail/events: no message text, no genes. */
export interface GuardrailEvent {
  ts: string;
  rule: string;
  outcome: "blocked" | "rewritten" | "escalated" | "passed";
  message_id: string;
}

export interface GateResult {
  passed: boolean;
  violations: { rule: GateRule | string; detail: string }[];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(code);
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let code = String(res.status);
    try {
      const body = (await res.json()) as { error?: { code?: string }; detail?: string };
      code = body.error?.code ?? body.detail ?? code;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, code);
  }
  return (await res.json()) as T;
}

export const getGuardrailEvents = () => req<GuardrailEvent[]>("/api/guardrail/events");

export const postGateProbe = (body: { recipient_partner_id: string; draft: string; lang: "en" | "ar" }) =>
  req<GateResult>("/api/demo/gate-probe", { method: "POST", body: JSON.stringify(body) });

/** The ten synthetic vignette partners (R-DATA-2). IDs only, no genotype data. */
export const RECIPIENTS = ["V1A", "V1B", "V2A", "V2B", "V3A", "V3B", "V4A", "V4B", "V5A", "V5B"] as const;
