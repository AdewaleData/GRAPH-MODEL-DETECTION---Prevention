"use client";

import { useEffect, useState } from "react";
import { LOCAL_DEV_API } from "@/lib/config-constants";
import { toWsUrl } from "@/lib/ws-url";

export type BackendConfig = {
  apiUrl: string;
  wsUrl: string;
};

let cached: BackendConfig | null = null;

/** Resolve WebSocket base URL (direct to Render when Vercel proxy is used for REST). */
export async function resolveBackendConfig(): Promise<BackendConfig> {
  if (cached) return cached;

  if (typeof window !== "undefined" && process.env.NODE_ENV === "production") {
    try {
      const res = await fetch("/api/backend-config");
      if (res.ok) {
        const data = (await res.json()) as BackendConfig;
        cached = { apiUrl: data.apiUrl, wsUrl: toWsUrl(data.apiUrl) };
        return cached;
      }
    } catch {
      /* fall through */
    }
  }

  const publicApi = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (publicApi) {
    cached = { apiUrl: publicApi, wsUrl: toWsUrl(publicApi) };
    return cached;
  }

  const { API_BASE_URL } = await import("@/lib/config");
  if (API_BASE_URL) {
    cached = { apiUrl: API_BASE_URL, wsUrl: toWsUrl(API_BASE_URL) };
    return cached;
  }

  cached = { apiUrl: LOCAL_DEV_API, wsUrl: toWsUrl(LOCAL_DEV_API) };
  return cached;
}

export function useBackendConfig() {
  const [config, setConfig] = useState<BackendConfig | null>(cached);

  useEffect(() => {
    let cancelled = false;
    resolveBackendConfig().then((c) => {
      if (!cancelled) setConfig(c);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return config;
}
