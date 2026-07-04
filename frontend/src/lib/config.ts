/** API configuration — override via NEXT_PUBLIC_* env at build time */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";
export const API_V1 = `${API_BASE_URL}/api/v1`;
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");

export const WS_CHANNELS = {
  alerts: `${WS_BASE_URL}/ws/alerts`,
  graph: `${WS_BASE_URL}/ws/graph`,
  traffic: `${WS_BASE_URL}/ws/traffic`,
  metrics: `${WS_BASE_URL}/ws/metrics`,
  mitigation: `${WS_BASE_URL}/ws/mitigation`,
} as const;
