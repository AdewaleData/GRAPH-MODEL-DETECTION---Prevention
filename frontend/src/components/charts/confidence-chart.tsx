"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function ConfidenceChart({
  data,
}: {
  data: { range: string; count: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3d" />
        <XAxis dataKey="range" stroke="#64748b" fontSize={10} />
        <YAxis stroke="#64748b" fontSize={11} />
        <Tooltip
          contentStyle={{
            background: "#151d2e",
            border: "1px solid #1e2a3d",
            borderRadius: 8,
          }}
        />
        <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="Detections" />
      </BarChart>
    </ResponsiveContainer>
  );
}
