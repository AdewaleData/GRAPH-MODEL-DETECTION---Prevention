"use client";

import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SeverityBadge } from "@/components/dashboard/severity-badge";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import { useRealtimeStore } from "@/store/realtime-store";
import type { Alert } from "@/types/api";
import { formatDetectionConfidence } from "@/lib/utils";

export default function AlertsPage() {
  const token = useAuthStore((s) => s.token)!;
  const wsAlerts = useRealtimeStore((s) => s.alerts);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const load = () => api.alerts(token).then(setAlerts).catch(console.error);

  useEffect(() => {
    load();
  }, [token]);

  const merged = [...wsAlerts, ...alerts.filter((a) => !wsAlerts.find((w) => w.id === a.id))];

  async function acknowledge(id: number) {
    await api.acknowledgeAlert(token, id);
    load();
  }

  return (
    <>
      <Header title="Security Alerts" subtitle="Attack detection notifications" />
      <main className="flex-1 overflow-y-auto p-6">
        <Card>
          <CardHeader>
            <CardTitle>All Alerts</CardTitle>
            <CardDescription>{merged.filter((a) => !a.acknowledged).length} need review</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {merged.map((a) => (
              <div
                key={a.id}
                className="flex flex-col gap-3 rounded-xl border border-border bg-surface/40 p-4 transition-all duration-200 hover:border-danger/30 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={a.severity} />
                    {a.acknowledged && (
                      <span className="text-xs text-success">Reviewed</span>
                    )}
                  </div>
                  <p className="font-medium text-white">{a.title}</p>
                  <p className="text-sm text-muted">{a.message}</p>
                  <p className="text-xs font-mono text-primary">{a.victim_ip}</p>
                  <p className="text-xs text-muted">
                    {new Date(a.created_at).toLocaleString()} · Confidence{" "}
                    {formatDetectionConfidence(true, a.probability)}
                  </p>
                </div>
                {!a.acknowledged && (
                  <Button variant="outline" size="sm" onClick={() => acknowledge(a.id)}>
                    <Check className="mr-1 h-4 w-4" />
                    Mark reviewed
                  </Button>
                )}
              </div>
            ))}
            {!merged.length && (
              <p className="py-16 text-center text-muted">No alerts. Your network looks healthy.</p>
            )}
          </CardContent>
        </Card>
      </main>
    </>
  );
}
