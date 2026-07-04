"use client";

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CytoscapeGraph } from "@/components/graph/cytoscape-graph";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import { useRealtimeStore } from "@/store/realtime-store";
import type { LiveGraph } from "@/types/api";
import { formatDetectionConfidence, formatPercent } from "@/lib/utils";

export default function GraphPage() {
  const token = useAuthStore((s) => s.token)!;
  const wsGraph = useRealtimeStore((s) => s.liveGraph);
  const [victimIp, setVictimIp] = useState("192.168.1.100");
  const [victims, setVictims] = useState<string[]>([]);
  const [graph, setGraph] = useState<LiveGraph | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.victims(token).then((r) => {
      setVictims(r.victims);
      if (r.victims[0]) setVictimIp(r.victims[0]);
    }).catch(() => {});
  }, [token]);

  const display = wsGraph ?? graph;

  async function refresh() {
    setLoading(true);
    try {
      const g = await api.liveGraph(token, victimIp);
      setGraph(g);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [token, victimIp]);

  return (
    <>
      <Header title="Network Graph" subtitle="Visualize traffic relationships in real time" />
      <main className="flex-1 overflow-y-auto p-6 space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className="mb-1 block text-xs text-muted">Target IP</label>
            <Input value={victimIp} onChange={(e) => setVictimIp(e.target.value)} list="victims-list" />
            <datalist id="victims-list">
              {victims.map((v) => (
                <option key={v} value={v} />
              ))}
            </datalist>
          </div>
          <Button onClick={refresh} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {display && (
          <div className="flex flex-wrap gap-2">
            <Badge variant="muted">{display.num_flows} flows</Badge>
            <Badge variant="muted">{display.nodes.length} nodes</Badge>
            <Badge variant="muted">{display.edges.length} links</Badge>
            {display.probability != null && (
              <Badge variant={display.is_attack ? "danger" : "success"}>
                {display.is_attack ? "Suspicious" : "Normal"} ·{" "}
                {formatDetectionConfidence(display.is_attack, display.probability)}
              </Badge>
            )}
          </div>
        )}

        <Card className="min-h-[500px]">
          <CardHeader>
            <CardTitle>Communication Graph</CardTitle>
            <CardDescription>
              Red node = target under attack · Purple border = sources · Arrows = traffic direction
            </CardDescription>
          </CardHeader>
          <CardContent className="h-[520px]">
            <CytoscapeGraph graph={display} />
          </CardContent>
        </Card>
      </main>
    </>
  );
}
