"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Server, XCircle } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { API_BASE_URL } from "@/lib/config";
import { useRealtimeStore } from "@/store/realtime-store";
import type { HealthStatus } from "@/types/api";

export default function HealthPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState(false);
  const connected = useRealtimeStore((s) => s.connected);
  const lastHeartbeat = useRealtimeStore((s) => s.lastHeartbeat);

  useEffect(() => {
    const check = () =>
      api
        .health()
        .then((h) => {
          setHealth(h);
          setError(false);
        })
        .catch(() => setError(true));
    check();
    const t = setInterval(check, 10000);
    return () => clearInterval(t);
  }, []);

  const channels = ["alerts", "graph", "traffic", "metrics"] as const;

  return (
    <>
      <Header title="System Health" subtitle="API, models, and live connection status" />
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-4 w-4 text-primary" />
                API Server
              </CardTitle>
              <CardDescription>{API_BASE_URL}</CardDescription>
            </CardHeader>
            <CardContent>
              {error ? (
                <div className="flex items-center gap-2 text-danger">
                  <XCircle className="h-5 w-5" />
                  <span>Offline — start the backend server</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-success">
                  <CheckCircle2 className="h-5 w-5" />
                  <span>{health?.status ?? "Checking…"}</span>
                  <Badge variant="muted">v{health?.version ?? "—"}</Badge>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI Models</CardTitle>
              <CardDescription>Loaded inference engines</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {health?.models &&
                Object.entries(health.models).map(([name, ok]) => (
                  <div key={name} className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
                    <span className="uppercase text-sm">{name}</span>
                    <Badge variant={ok ? "success" : "danger"}>{ok ? "Ready" : "Unavailable"}</Badge>
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Live Channels</CardTitle>
            <CardDescription>
              WebSocket streams · Last ping {lastHeartbeat ? new Date(lastHeartbeat).toLocaleTimeString() : "—"}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {channels.map((ch) => (
              <div
                key={ch}
                className="rounded-lg border border-border bg-surface/50 p-4 transition-all hover:border-secondary/40"
              >
                <p className="text-xs uppercase text-muted">{ch}</p>
                <p className="mt-2 flex items-center gap-2 text-sm font-medium">
                  <span
                    className={`h-2 w-2 rounded-full ${connected[ch] ? "bg-success animate-pulse-soft" : "bg-muted"}`}
                  />
                  {connected[ch] ? "Connected" : "Reconnecting…"}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </main>
    </>
  );
}
