"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { useRealtimeStore } from "@/store/realtime-store";
import type { PredictionHistory } from "@/types/api";

const POLL_MS = 4000;

function historyToTraffic(rows: PredictionHistory[]) {
  return rows.slice(0, 80).map((r) => ({
    victim_ip: r.victim_ip,
    is_attack: r.is_attack,
    probability: r.probability,
    model: r.model_name,
    ts: r.created_at,
  }));
}

/** REST polling fallback — keeps dashboard live when WebSockets fail (common on Vercel). */
export function useLivePolling(token: string | null) {
  const setAlerts = useRealtimeStore((s) => s.setAlerts);
  const setLiveGraph = useRealtimeStore((s) => s.setLiveGraph);
  const syncTrafficFromHistory = useRealtimeStore((s) => s.syncTrafficFromHistory);

  useEffect(() => {
    if (!token) return;

    let active = true;

    const poll = async () => {
      try {
        const [history, alerts, victimsRes] = await Promise.all([
          api.history(token, 50),
          api.alerts(token, false),
          api.victims(token).catch(() => ({ victims: [] as string[] })),
        ]);
        if (!active) return;

        setAlerts(alerts);
        syncTrafficFromHistory(historyToTraffic(history));

        const victims = victimsRes.victims;
        if (victims.length > 0) {
          const victim = victims[victims.length - 1];
          try {
            const graph = await api.liveGraph(token, victim);
            if (active) setLiveGraph(graph);
          } catch {
            /* buffer may be empty between ticks */
          }
        }
      } catch (err) {
        console.error("Live poll failed:", err);
      }
    };

    poll();
    const timer = setInterval(poll, POLL_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [token, setAlerts, setLiveGraph, syncTrafficFromHistory]);
}
