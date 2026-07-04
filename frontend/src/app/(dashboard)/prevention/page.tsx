"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Ban, Clock, RotateCcw, ShieldBan, Zap } from "lucide-react";
import { toast } from "sonner";
import { Header } from "@/components/layout/header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import { useRealtimeStore } from "@/store/realtime-store";
import type { MitigationRecord, MitigationSummary, PreventionStats } from "@/types/api";

const ACTION_COLORS: Record<string, string> = {
  block: "bg-danger/20 text-danger border-danger/30",
  rate_limit: "bg-secondary/20 text-secondary border-secondary/30",
  quarantine: "bg-primary/20 text-primary border-primary/30",
};

const POLL_MS = 3000;

export default function PreventionPage() {
  const token = useAuthStore((s) => s.token)!;
  const wsMitigations = useRealtimeStore((s) => s.mitigations);
  const setMitigations = useRealtimeStore((s) => s.setMitigations);
  const [records, setRecords] = useState<MitigationRecord[]>([]);
  const [summary, setSummary] = useState<MitigationSummary | null>(null);
  const [stats, setStats] = useState<PreventionStats | null>(null);

  const load = useCallback(() => {
    Promise.all([
      api.mitigationActive(token),
      api.mitigationHistory(token, 50),
      api.mitigationSummary(token),
      api.preventionStats(token),
    ])
      .then(([active, history, sum, st]) => {
        setRecords(history);
        setMitigations(active);
        setSummary(sum);
        setStats(st);
      })
      .catch(console.error);
  }, [token, setMitigations]);

  useEffect(() => {
    load();
    const t = setInterval(load, POLL_MS);
    const onLive = () => load();
    window.addEventListener("halal-prevention-stats", onLive);
    return () => {
      clearInterval(t);
      window.removeEventListener("halal-prevention-stats", onLive);
    };
  }, [load]);

  useEffect(() => {
    if (wsMitigations.length) load();
  }, [wsMitigations.length, load]);

  const historyMerged = useMemo(() => {
    const map = new Map<number, MitigationRecord>();
    for (const r of records) map.set(r.id, r);
    for (const w of wsMitigations) {
      if (w.id) map.set(w.id, w as MitigationRecord);
    }
    return Array.from(map.values()).sort(
      (a, b) => new Date(b.applied_at).getTime() - new Date(a.applied_at).getTime(),
    );
  }, [records, wsMitigations]);

  const activeMerged = useMemo(
    () => historyMerged.filter((r) => r.status === "active"),
    [historyMerged],
  );

  async function revoke(id: number) {
    try {
      await api.revokeMitigation(token, id);
      toast.success("Prevention rule revoked");
      load();
    } catch (e) {
      toast.error(String(e));
    }
  }

  return (
    <>
      <Header
        title="Attack Prevention"
        subtitle="Automated mitigation from GNN detection: block, rate-limit, or quarantine attacker sources"
      />
      <main className="flex-1 overflow-y-auto p-4 space-y-4 sm:p-6 sm:space-y-6">
        <div className="grid gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
          <MetricCard
            title="Active Rules"
            value={summary?.total_active ?? activeMerged.length}
            subtitle={`${summary?.active_blocks ?? 0} blocks · ${summary?.active_rate_limits ?? 0} rate limits`}
            icon={ShieldBan}
            accent="danger"
          />
          <MetricCard
            title="Flows Blocked"
            value={stats?.flows_blocked ?? 0}
            subtitle="Dropped at ingest by blocklist"
            icon={Ban}
            accent="secondary"
          />
          <MetricCard
            title="Time to Mitigate"
            value={summary ? `${summary.avg_time_to_mitigate_ms.toFixed(1)}ms` : "0ms"}
            subtitle="Detection → prevention action"
            icon={Zap}
            accent="success"
          />
          <MetricCard
            title="Enforcement Mode"
            value={summary?.mode ?? "simulated"}
            subtitle={summary?.auto_enabled ? "Auto-prevention ON" : "Manual only"}
            icon={Clock}
            accent="primary"
          />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Active Prevention Rules</CardTitle>
            <CardDescription>
              Auto-applied on attack patterns: critical blocks, high rate-limits, medium quarantine
            </CardDescription>
          </CardHeader>
          <CardContent className="max-h-[420px] space-y-3 overflow-y-auto">
            {activeMerged.map((r) => (
              <div
                key={r.id}
                className="flex flex-col gap-3 rounded-xl border border-border bg-surface/40 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className={ACTION_COLORS[r.action] ?? "bg-panel text-white"}>{r.action}</Badge>
                    {r.auto_triggered && (
                      <span className="text-[10px] uppercase tracking-wider text-muted">Auto</span>
                    )}
                    <span className="text-xs text-success">{r.detection_to_action_ms.toFixed(1)}ms MTTM</span>
                  </div>
                  <p className="font-mono text-sm text-white">
                    {r.source_ip} → {r.victim_ip}
                  </p>
                  <p className="text-sm text-muted">{r.reason}</p>
                  {r.rule_text && (
                    <p className="font-mono text-xs text-primary/80">{r.rule_text}</p>
                  )}
                  <p className="text-xs text-muted">{new Date(r.applied_at).toLocaleString()}</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => revoke(r.id)}>
                  <RotateCcw className="mr-1 h-4 w-4" />
                  Revoke
                </Button>
              </div>
            ))}
            {!activeMerged.length && (
              <p className="py-12 text-center text-muted">No active prevention rules. Network is clear.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Mitigation History</CardTitle>
            <CardDescription>Live audit trail — updates every {POLL_MS / 1000}s and on each prevention action</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
                    <th className="pb-2 pr-4">Source</th>
                    <th className="pb-2 pr-4">Victim</th>
                    <th className="pb-2 pr-4">Action</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2 pr-4">Score</th>
                    <th className="pb-2">Applied</th>
                  </tr>
                </thead>
                <tbody>
                  {historyMerged.slice(0, 30).map((r) => (
                    <tr key={r.id} className="border-b border-border/50 text-muted hover:text-white">
                      <td className="py-2 pr-4 font-mono text-xs">{r.source_ip}</td>
                      <td className="py-2 pr-4 font-mono text-xs">{r.victim_ip}</td>
                      <td className="py-2 pr-4">{r.action}</td>
                      <td className="py-2 pr-4">
                        <span className={r.status === "active" ? "text-danger" : "text-muted"}>{r.status}</span>
                      </td>
                      <td className="py-2 pr-4">{r.score.toFixed(1)}</td>
                      <td className="py-2">{new Date(r.applied_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!historyMerged.length && (
                <p className="py-8 text-center text-muted">No mitigation history yet.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </main>
    </>
  );
}
