import { API_BASE_URL, API_V1 } from "./config";
import type {
  Alert,
  HealthStatus,
  LiveGraph,
  MetricsSummary,
  MitigationRecord,
  MitigationSummary,
  PredictResponse,
  PredictionHistory,
  PreventionStats,
  TokenResponse,
} from "@/types/api";
import type { FlowRecord } from "@/types/api";

/** Turn FastAPI `detail` (string, object, or validation array) into readable text */
export function formatApiDetail(detail: unknown): string {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const loc = "loc" in item && Array.isArray(item.loc) ? item.loc.join(".") : "";
          return loc ? `${loc}: ${String(item.msg)}` : String(item.msg);
        }
        return String(item);
      })
      .join(" ");
  }
  if (typeof detail === "object" && "msg" in detail) return String((detail as { msg: unknown }).msg);
  return "Something went wrong. Please try again.";
}

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_V1}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(formatApiDetail(body.detail) || res.statusText || "Request failed", res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetch(`${API_BASE_URL}/health`).then((r) => r.json() as Promise<HealthStatus>),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  metrics: (token: string) => request<MetricsSummary>("/metrics", {}, token),

  history: (token: string, limit = 50) =>
    request<PredictionHistory[]>(`/metrics/history?limit=${limit}`, {}, token),

  alerts: (token: string, unacknowledgedOnly = false) =>
    request<Alert[]>(`/alerts?unacknowledged_only=${unacknowledgedOnly}`, {}, token),

  acknowledgeAlert: (token: string, alertId: number) =>
    request<Alert>("/alerts/acknowledge", {
      method: "POST",
      body: JSON.stringify({ alert_id: alertId }),
    }, token),

  liveGraph: (token: string, victimIp: string) =>
    request<LiveGraph>(`/graph/live/${encodeURIComponent(victimIp)}`, {}, token),

  victims: (token: string) =>
    request<{ victims: string[] }>("/graph/victims", {}, token),

  predict: (token: string, flows: FlowRecord[], model = "gcn") =>
    request<PredictResponse>("/predict", {
      method: "POST",
      body: JSON.stringify({ flows, model }),
    }, token),

  mitigationActive: (token: string) =>
    request<MitigationRecord[]>("/mitigation/active", {}, token),

  mitigationHistory: (token: string, limit = 100) =>
    request<MitigationRecord[]>(`/mitigation/history?limit=${limit}`, {}, token),

  mitigationSummary: (token: string) =>
    request<MitigationSummary>("/mitigation/summary", {}, token),

  preventionStats: (token: string) =>
    request<PreventionStats>("/mitigation/stats", {}, token),

  applyMitigation: (
    token: string,
    sourceIp: string,
    victimIp: string,
    action: string,
    reason?: string,
  ) =>
    request<MitigationRecord>("/mitigation/apply", {
      method: "POST",
      body: JSON.stringify({
        source_ip: sourceIp,
        victim_ip: victimIp,
        action,
        reason: reason ?? "Manual prevention action",
      }),
    }, token),

  revokeMitigation: (token: string, recordId: number) =>
    request<MitigationRecord[]>("/mitigation/revoke", {
      method: "POST",
      body: JSON.stringify({ record_id: recordId }),
    }, token),
};

export { ApiError };
