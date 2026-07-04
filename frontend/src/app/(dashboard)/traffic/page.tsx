"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrafficChart } from "@/components/charts/traffic-chart";
import { useRealtimeStore } from "@/store/realtime-store";
import { useAuthStore } from "@/store/auth-store";
import { api } from "@/lib/api";
import type { PredictionHistory } from "@/types/api";
import { formatPercent } from "@/lib/utils";

export default function TrafficPage() {
  const token = useAuthStore((s) => s.token)!;
  const trafficEvents = useRealtimeStore((s) => s.trafficEvents);
  const [history, setHistory] = useState<PredictionHistory[]>([]);

  useEffect(() => {
    api.history(token, 100).then(setHistory).catch(console.error);
  }, [token]);

  const rows = trafficEvents.length
    ? trafficEvents.map((e, i) => ({
        id: i,
        victim_ip: e.victim_ip,
        is_attack: e.is_attack,
        probability: e.probability,
        model: e.model,
        created_at: e.ts,
      }))
    : history;

  const chartData = rows.slice(0, 24).map((r, i) => ({
    time: `${23 - i}`,
    attacks: r.is_attack ? 1 : 0,
    benign: r.is_attack ? 0 : 1,
  }));

  return (
    <>
      <Header title="Live Traffic" subtitle="Streaming network flow analysis" />
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Traffic Flow</CardTitle>
            <CardDescription>Real-time classification stream</CardDescription>
          </CardHeader>
          <CardContent>
            <TrafficChart data={chartData.length ? chartData : [{ time: "0", attacks: 0, benign: 0 }]} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Flow Log</CardTitle>
            <CardDescription>Each row is one analyzed traffic window</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase text-muted">
                  <th className="pb-3 pr-4">Time</th>
                  <th className="pb-3 pr-4">Target IP</th>
                  <th className="pb-3 pr-4">Result</th>
                  <th className="pb-3 pr-4">Confidence</th>
                  <th className="pb-3">Model</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 50).map((r, i) => (
                  <tr
                    key={`${r.victim_ip}-${i}`}
                    className="border-b border-border/50 transition-colors hover:bg-panel/50"
                  >
                    <td className="py-3 pr-4 font-mono text-xs text-muted">
                      {new Date(r.created_at).toLocaleTimeString()}
                    </td>
                    <td className="py-3 pr-4 font-mono text-primary">{r.victim_ip}</td>
                    <td className="py-3 pr-4">
                      <Badge variant={r.is_attack ? "danger" : "success"} pulse={r.is_attack}>
                        {r.is_attack ? "Suspicious" : "Normal"}
                      </Badge>
                    </td>
                    <td className="py-3 pr-4 tabular-nums">{formatPercent(r.probability)}</td>
                    <td className="py-3 uppercase text-xs text-secondary">
                      {"model" in r ? r.model : r.model_name}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!rows.length && (
              <p className="py-12 text-center text-muted">No traffic data yet. Run a prediction on the backend.</p>
            )}
          </CardContent>
        </Card>
      </main>
    </>
  );
}
