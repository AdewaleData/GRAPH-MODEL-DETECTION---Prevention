"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL, WS_BASE_URL } from "@/lib/config";

export type BackendConfig = {
  apiUrl: string;
  wsUrl: string;
};

let cached: BackendConfig | null = null;

/** Resolve WebSocket base URL (direct to Render when Vercel proxy is used for REST). */
export async function resolveBackendConfig(): Promise<BackendConfig> {
  if (cached) return cached;

  const publicApi = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (publicApi) {
    cached = { apiUrl: publicApi, wsUrl: publicApi.replace(/^http/, "ws") };
    return cached;
  }

  if (API_BASE_URL) {
    cached = { apiUrl: API_BASE_URL, wsUrl: WS_BASE_URL };
    return cached;
  }

  if (typeof window !== "undefined" && process.env.NODE_ENV === "production") {
    try {
      const res = await fetch("/api/backend-config");
      if (res.ok) {
        cached = (await res.json()) as BackendConfig;
        return cached;
      }
    } catch {
      /* fall through */
    }
  }

  cached = { apiUrl: "http://127.0.0.1:8000", wsUrl: "ws://127.0.0.1:8000" };
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
