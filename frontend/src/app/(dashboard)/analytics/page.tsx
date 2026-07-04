"use client";

import { Header } from "@/components/layout/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfusionMatrix } from "@/components/charts/confusion-matrix";
import { ConfidenceChart } from "@/components/charts/confidence-chart";
import { MODEL_BENCHMARKS } from "@/lib/model-stats";
import { formatPercent } from "@/lib/utils";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const compareData = Object.entries(MODEL_BENCHMARKS).map(([key, m]) => ({
  model: key.toUpperCase(),
  f1: m.f1 * 100,
  recall: m.recall * 100,
  precision: m.precision * 100,
}));

const confidenceBuckets = [
  { range: "0–20%", count: 120 },
  { range: "20–40%", count: 340 },
  { range: "40–60%", count: 890 },
  { range: "60–80%", count: 2100 },
  { range: "80–100%", count: 4550 },
];

export default function AnalyticsPage() {
  return (
    <>
      <Header title="Model Analytics" subtitle="How well each detector performs" />
      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          {Object.entries(MODEL_BENCHMARKS).map(([key, m]) => (
            <Card key={key} className="transition-transform hover:scale-[1.01]">
              <CardHeader>
                <CardTitle>{m.name}</CardTitle>
                <CardDescription>Offline evaluation (CICDDoS2019)</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-muted text-xs">F1 Score</p>
                  <p className="text-xl font-bold text-white">{formatPercent(m.f1)}</p>
                </div>
                <div>
                  <p className="text-muted text-xs">Recall</p>
                  <p className="text-xl font-bold text-secondary">{formatPercent(m.recall)}</p>
                </div>
                <div>
                  <p className="text-muted text-xs">Precision</p>
                  <p className="text-xl font-bold text-primary">{formatPercent(m.precision)}</p>
                </div>
                <div>
                  <p className="text-muted text-xs">Speed</p>
                  <p className="text-xl font-bold text-success">{m.latencyMs}ms</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Model Comparison</CardTitle>
              <CardDescription>F1, recall, and precision (%)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={compareData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3d" />
                  <XAxis dataKey="model" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: "#151d2e", border: "1px solid #1e2a3d" }} />
                  <Legend />
                  <Bar dataKey="f1" fill="#06b6d4" name="F1" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="recall" fill="#8b5cf6" name="Recall" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="precision" fill="#10b981" name="Precision" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Detection Confidence</CardTitle>
              <CardDescription>Distribution of prediction scores</CardDescription>
            </CardHeader>
            <CardContent>
              <ConfidenceChart data={confidenceBuckets} />
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {Object.entries(MODEL_BENCHMARKS).map(([key, m]) => (
            <Card key={`cm-${key}`}>
              <CardHeader>
                <CardTitle>{m.name}</CardTitle>
                <CardDescription>Confusion matrix</CardDescription>
              </CardHeader>
              <CardContent>
                <ConfusionMatrix matrix={m.confusion} />
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </>
  );
}
