"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, Brain, Gauge, ShieldAlert, Zap } from "lucide-react";
import { Header } from "@/components/layout/header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TrafficChart } from "@/components/charts/traffic-chart";
import { CytoscapeGraph } from "@/components/graph/cytoscape-graph";
import { SeverityBadge } from "@/components/dashboard/severity-badge";
import { api } from "@/lib/api";
import { formatPercent } from "@/lib/utils";
import { displayMetric, useMetrics } from "@/hooks/use-metrics";
import { useBackendConfig } from "@/hooks/use-backend-config";
import { useAuthStore } from "@/store/auth-store";
import { useRealtimeStore } from "@/store/realtime-store";
import type { DemoStatus } from "@/types/api";

export default function DashboardPage() {
  const token = useAuthStore((s) => s.token)!;
  const { metrics, loading, error, refresh } = useMetrics(token);
  const alerts = useRealtimeStore((s) => s.alerts);
  const setAlerts = useRealtimeStore((s) => s.setAlerts);
  const liveGraph = useRealtimeStore((s) => s.liveGraph);
  const trafficEvents = useRealtimeStore((s) => s.trafficEvents);
  const connected = useRealtimeStore((s) => s.connected);
  const liveFeeds = Object.values(connected).filter(Boolean).length;
  const backendConfig = useBackendConfig();
  const [demo, setDemo] = useState<DemoStatus | null>(null);

  useEffect(() => {
    api.alerts(token, false).then(setAlerts).catch(console.error);
  }, [token, setAlerts]);

  useEffect(() => {
    const loadDemo = () => api.demoStatus(token).then(setDemo).catch(() => setDemo(null));
    loadDemo();
    const t = setInterval(loadDemo, 10000);
    return () => clearInterval(t);
  }, [token]);

  useEffect(() => {
    if (trafficEvents.length) refresh();
  }, [trafficEvents.length, refresh]);

  const loaded = !loading && !error;
  const chartData = useMemo(() => {
    const buckets: Record<string, { attacks: number; benign: number }> = {};
    for (let i = 11; i >= 0; i--) {
      const label = `${i * 5}s`;
      buckets[label] = { attacks: 0, benign: 0 };
    }
    trafficEvents.slice(0, 60).forEach((e, idx) => {
      const label = `${Math.floor(idx / 5) * 5}s`;
      if (!buckets[label]) buckets[label] = { attacks: 0, benign: 0 };
      if (e.is_attack) buckets[label].attacks++;
      else buckets[label].benign++;
    });
    return Object.entries(buckets)
      .map(([time, v]) => ({ time, ...v }))
      .reverse();
  }, [trafficEvents]);

  return (
    <>
      <Header
        title="Security Overview"
        subtitle="Real-time DDoS detection using Graph Neural Networks"
      />
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {error && (
          <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
            Metrics unavailable: {error}. Check API connection and sign in again if needed.
          </div>
        )}

        {!error && loaded && (metrics?.total_predictions ?? 0) === 0 && (
          <div className="rounded-lg border border-secondary/30 bg-secondary/10 px-4 py-3 text-sm text-secondary space-y-1">
            <p>No scans recorded yet. Data refreshes every 4 seconds via the API.</p>
            {demo && (
              <p className="text-xs text-muted">
                Simulator: {demo.simulator_running ? "running" : "stopped"}
                {demo.simulator_enabled ? "" : " (disabled on server)"}
                {" · "}
                {demo.traffic_windows} traffic windows
                {" · "}
                GCN {demo.models.gcn ? "loaded" : "missing"}
                {backendConfig ? ` · API ${backendConfig.apiUrl}` : ""}
                {liveFeeds === 0 ? " · WebSockets offline (REST polling active)" : ` · ${liveFeeds}/5 live feeds`}
              </p>
            )}
            {!demo?.models.gcn && (
              <p className="text-xs text-warn">
                Backend model not loaded. Upgrade Render to Standard (2 GB) or check deploy logs for OOM errors.
              </p>
            )}
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <MetricCard
            title="Total Scans"
            value={displayMetric(metrics?.total_predictions, loaded)}
            subtitle="All traffic analyzed"
            icon={Activity}
            accent="primary"
          />
          <MetricCard
            title="Threats Found"
            value={displayMetric(metrics?.attack_predictions, loaded)}
            subtitle={metrics ? `${formatPercent(metrics.attack_rate)} of traffic` : "Attack rate"}
            icon={ShieldAlert}
            trend="up"
            accent="danger"
          />
          <MetricCard
            title="Open Alerts"
            value={
              loaded
                ? (metrics?.unacknowledged_alerts ?? alerts.filter((a) => !a.acknowledged).length)
                : "..."
            }
            subtitle="Needs your attention"
            icon={AlertTriangle}
            accent="secondary"
          />
          <MetricCard
            title="Active Blocks"
            value={displayMetric(metrics?.active_mitigations, loaded)}
            subtitle={
              metrics ? `${metrics.flows_blocked} flows filtered` : "Prevention rules"
            }
            icon={ShieldAlert}
            accent="primary"
          />
          <MetricCard
            title="Response Time"
            value={
              loaded && metrics
                ? `${metrics.avg_latency_ms.toFixed(1)}ms`
                : displayMetric(null, loaded, "...")
            }
            subtitle={
              metrics?.avg_time_to_mitigate_ms
                ? `Mitigate in ${metrics.avg_time_to_mitigate_ms.toFixed(0)}ms`
                : "Average per scan"
            }
            icon={Zap}
            accent="success"
          />
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Traffic Activity</CardTitle>
              <CardDescription>Live flow of normal vs suspicious traffic</CardDescription>
            </CardHeader>
            <CardContent>
              <TrafficChart data={chartData} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-secondary" />
                Model Status
              </CardTitle>
              <CardDescription>Models ready for inference</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {["GCN", "GAT", "Random Forest"].map((m) => (
                <div
                  key={m}
                  className="flex items-center justify-between rounded-lg border border-border bg-surface/50 px-3 py-2.5 transition-colors hover:border-primary/30"
                >
                  <span className="text-sm text-white">{m}</span>
                  <span className="flex items-center gap-2 text-xs text-success">
                    <Gauge className="h-3 w-3" />
                    Online
                  </span>
                </div>
              ))}
              <p className="text-xs text-muted">
                Graph models analyze traffic windows per destination IP for coordinated attack patterns.
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Live Network Graph</CardTitle>
              <CardDescription>
                {liveGraph?.victim_ip ? `Target: ${liveGraph.victim_ip}` : "Waiting for graph updates"}
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[360px]">
              <CytoscapeGraph graph={liveGraph} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Alerts</CardTitle>
              <CardDescription>Latest security notifications</CardDescription>
            </CardHeader>
            <CardContent className="max-h-[360px] space-y-2 overflow-y-auto">
              {alerts.slice(0, 8).map((a) => (
                <div
                  key={a.id}
                  className="flex items-start justify-between gap-2 rounded-lg border border-border bg-surface/40 p-3 transition-all hover:border-secondary/30"
                >
                  <div>
                    <p className="text-sm font-medium text-white">{a.title}</p>
                    <p className="text-xs text-muted mt-0.5">{a.victim_ip}</p>
                  </div>
                  <SeverityBadge severity={a.severity} />
                </div>
              ))}
              {!alerts.length && (
                <p className="py-8 text-center text-sm text-muted">
                  No alerts yet. Your network looks clear.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </>
  );
}
