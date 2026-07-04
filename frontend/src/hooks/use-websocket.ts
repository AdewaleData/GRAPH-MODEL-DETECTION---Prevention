"use client";

import { useEffect } from "react";
import { toast } from "sonner";
import { resolveBackendConfig } from "@/hooks/use-backend-config";
import { useRealtimeStore } from "@/store/realtime-store";
import type { LiveGraph } from "@/types/api";

function connectChannel(
  wsBase: string,
  path: string,
  name: string,
  onMessage: (data: unknown) => void,
) {
  let ws: WebSocket | null = null;
  let retryTimer: ReturnType<typeof setTimeout>;
  const { setConnected } = useRealtimeStore.getState();
  const url = `${wsBase}${path}`;

  const connect = () => {
    try {
      ws = new WebSocket(url);
      ws.onopen = () => setConnected(name, true);
      ws.onclose = () => {
        setConnected(name, false);
        retryTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws?.close();
      ws.onmessage = (ev) => {
        try {
          onMessage(JSON.parse(ev.data));
        } catch {
          /* ignore */
        }
      };
    } catch {
      retryTimer = setTimeout(connect, 3000);
    }
  };

  connect();
  return () => {
    clearTimeout(retryTimer);
    ws?.close();
    setConnected(name, false);
  };
}

export function useWebSockets(enabled: boolean) {
  const pushAlert = useRealtimeStore((s) => s.pushAlert);
  const pushMitigation = useRealtimeStore((s) => s.pushMitigation);
  const revokeMitigation = useRealtimeStore((s) => s.revokeMitigation);
  const setLiveGraph = useRealtimeStore((s) => s.setLiveGraph);
  const pushTraffic = useRealtimeStore((s) => s.pushTraffic);
  const setHeartbeat = useRealtimeStore((s) => s.setHeartbeat);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;
    const cleaners: Array<() => void> = [];

    resolveBackendConfig().then(({ wsUrl }) => {
      if (cancelled) return;

      cleaners.push(
        connectChannel(wsUrl, "/ws/alerts", "alerts", (data) => {
          const d = data as Record<string, unknown>;
          if (d.type === "alert") {
            pushAlert(d as never);
            toast.error(d.title as string, { description: d.message as string });
          }
        }),
      );

      cleaners.push(
        connectChannel(wsUrl, "/ws/graph", "graph", (data) => {
          const d = data as { type?: string } & LiveGraph;
          if (d.type === "graph_update") setLiveGraph(d);
        }),
      );

      cleaners.push(
        connectChannel(wsUrl, "/ws/traffic", "traffic", (data) => {
          const d = data as Record<string, unknown>;
          if (d.type === "prediction") {
            pushTraffic({
              victim_ip: d.victim_ip as string,
              is_attack: d.is_attack as boolean,
              probability: d.probability as number,
              model: d.model as string,
              ts: new Date().toISOString(),
            });
          }
        }),
      );

      cleaners.push(
        connectChannel(wsUrl, "/ws/metrics", "metrics", (data) => {
          const d = data as { type?: string; ts?: string };
          if (d.type === "heartbeat" && d.ts) setHeartbeat(d.ts);
          if (d.type === "summary") {
            window.dispatchEvent(new CustomEvent("halal-metrics-summary", { detail: d }));
          }
        }),
      );

      cleaners.push(
        connectChannel(wsUrl, "/ws/mitigation", "mitigation", (data) => {
          const d = data as Record<string, unknown>;
          if (d.type === "mitigation_applied") {
            pushMitigation(d as never);
            if (!d.auto_triggered) {
              toast.warning("Prevention action applied", {
                description: `${d.action as string} on ${d.source_ip as string}`,
              });
            }
          }
          if (d.type === "mitigation_revoked") {
            revokeMitigation(d.id as number);
            toast.info("Prevention rule revoked", { description: d.source_ip as string });
          }
          if (d.type === "flows_filtered") {
            toast.message("Blocked traffic filtered", {
              description: `${d.count as number} flow(s) from blocked sources dropped`,
            });
          }
          if (d.type === "prevention_stats") {
            window.dispatchEvent(new CustomEvent("halal-prevention-stats", { detail: d }));
          }
        }),
      );
    });

    return () => {
      cancelled = true;
      cleaners.forEach((fn) => fn());
    };
  }, [
    enabled,
    pushAlert,
    pushMitigation,
    revokeMitigation,
    setLiveGraph,
    pushTraffic,
    setHeartbeat,
  ]);
}
