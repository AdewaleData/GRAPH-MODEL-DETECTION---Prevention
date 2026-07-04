import { create } from "zustand";
import type { Alert, LiveGraph, MitigationRecord } from "@/types/api";

interface TrafficEvent {
  victim_ip: string;
  is_attack: boolean;
  probability: number;
  model: string;
  ts: string;
}

interface RealtimeState {
  alerts: Alert[];
  mitigations: MitigationRecord[];
  liveGraph: LiveGraph | null;
  trafficEvents: TrafficEvent[];
  connected: Record<string, boolean>;
  lastHeartbeat: string | null;
  pushAlert: (alert: Partial<Alert> & { type?: string }) => void;
  pushMitigation: (record: Partial<MitigationRecord> & { type?: string }) => void;
  revokeMitigation: (recordId: number) => void;
  setLiveGraph: (graph: LiveGraph) => void;
  pushTraffic: (event: TrafficEvent) => void;
  syncTrafficFromHistory: (events: TrafficEvent[]) => void;
  setConnected: (channel: string, value: boolean) => void;
  setHeartbeat: (ts: string) => void;
  setAlerts: (alerts: Alert[]) => void;
  setMitigations: (records: MitigationRecord[]) => void;
}

export const useRealtimeStore = create<RealtimeState>((set) => ({
  alerts: [],
  mitigations: [],
  liveGraph: null,
  trafficEvents: [],
  connected: {},
  lastHeartbeat: null,
  pushAlert: (payload) =>
    set((s) => ({
      alerts: [
        {
          id: payload.id ?? Date.now(),
          victim_ip: payload.victim_ip ?? "unknown",
          severity: payload.severity ?? "medium",
          title: payload.title ?? "Activity detected",
          message: payload.message ?? "",
          probability: payload.probability ?? 0,
          acknowledged: false,
          created_at: new Date().toISOString(),
        },
        ...s.alerts,
      ].slice(0, 100),
    })),
  pushMitigation: (payload) =>
    set((s) => ({
      mitigations: [
        {
          id: payload.id ?? Date.now(),
          source_ip: payload.source_ip ?? "unknown",
          victim_ip: payload.victim_ip ?? "unknown",
          action: payload.action ?? "block",
          status: payload.status ?? "active",
          score: payload.score ?? 0,
          reason: payload.reason ?? "",
          rule_text: payload.rule_text ?? null,
          alert_id: payload.alert_id ?? null,
          prediction_id: payload.prediction_id ?? null,
          auto_triggered: payload.auto_triggered ?? true,
          detection_to_action_ms: payload.detection_to_action_ms ?? 0,
          applied_at: payload.applied_at ?? new Date().toISOString(),
          revoked_at: payload.revoked_at ?? null,
        },
        ...s.mitigations.filter((m) => m.id !== payload.id),
      ].slice(0, 100),
    })),
  revokeMitigation: (recordId) =>
    set((s) => ({
      mitigations: s.mitigations.map((m) =>
        m.id === recordId ? { ...m, status: "revoked", revoked_at: new Date().toISOString() } : m,
      ),
    })),
  setLiveGraph: (graph) => set({ liveGraph: graph }),
  pushTraffic: (event) =>
    set((s) => ({
      trafficEvents: [{ ...event, ts: event.ts || new Date().toISOString() }, ...s.trafficEvents].slice(0, 80),
    })),
  syncTrafficFromHistory: (events) => set({ trafficEvents: events }),
  setConnected: (channel, value) =>
    set((s) => ({ connected: { ...s.connected, [channel]: value } })),
  setHeartbeat: (ts) => set({ lastHeartbeat: ts }),
  setAlerts: (alerts) => set({ alerts }),
  setMitigations: (mitigations) => set({ mitigations }),
}));
