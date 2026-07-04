/** API configuration — override via NEXT_PUBLIC_* env at build time */

import { toWsUrl } from "./ws-url";
import { LOCAL_DEV_API } from "./config-constants";

/** Direct backend URL when set (required for WebSockets on Vercel). */
const PUBLIC_API = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

/**
 * REST base URL.
 * - Vercel/production without NEXT_PUBLIC: same-origin (proxied via next.config rewrites).
 * - Local dev: localhost:8000 unless NEXT_PUBLIC_API_URL is set.
 */
export const API_BASE_URL =
  PUBLIC_API ?? (process.env.NODE_ENV === "production" ? "" : LOCAL_DEV_API);

export const API_V1 = `${API_BASE_URL}/api/v1`;

/** WebSockets must hit the backend directly — proxy does not support WS. */
const WS_HTTP_BASE = PUBLIC_API ?? (API_BASE_URL || LOCAL_DEV_API);
export const WS_BASE_URL = toWsUrl(WS_HTTP_BASE);

export const WS_CHANNELS = {
  alerts: `${WS_BASE_URL}/ws/alerts`,
  graph: `${WS_BASE_URL}/ws/graph`,
  traffic: `${WS_BASE_URL}/ws/traffic`,
  metrics: `${WS_BASE_URL}/ws/metrics`,
  mitigation: `${WS_BASE_URL}/ws/mitigation`,
} as const;

/** Human-readable target for connection error messages. */
export function describeApiTarget(): string {
  if (API_BASE_URL) return API_BASE_URL;
  if (typeof window !== "undefined") return `${window.location.origin} (proxied to Render)`;
  return LOCAL_DEV_API;
}
