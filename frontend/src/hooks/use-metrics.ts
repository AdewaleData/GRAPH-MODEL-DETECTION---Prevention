"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MetricsSummary } from "@/types/api";

export function useMetrics(token: string) {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    return api
      .metrics(token)
      .then((m) => {
        setMetrics(m);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Could not load metrics");
      })
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    const onSummary = (e: Event) => {
      const detail = (e as CustomEvent<MetricsSummary>).detail;
      if (detail?.total_predictions !== undefined) {
        setMetrics(detail);
        setError(null);
        setLoading(false);
      }
    };
    window.addEventListener("halal-metrics-summary", onSummary);
    return () => {
      clearInterval(t);
      window.removeEventListener("halal-metrics-summary", onSummary);
    };
  }, [refresh]);

  return { metrics, loading, error, refresh };
}

/** Display helper: no em dashes; show 0 when loaded with no data. */
export function displayMetric(
  value: number | string | null | undefined,
  loaded: boolean,
  fallback: string | number = 0,
): string | number {
  if (!loaded) return "...";
  if (value === null || value === undefined) return fallback;
  return value;
}
