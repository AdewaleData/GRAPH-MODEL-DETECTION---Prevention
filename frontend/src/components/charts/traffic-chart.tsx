"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function TrafficChart({
  data,
}: {
  data: { time: string; attacks: number; benign: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3d" />
        <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
        <YAxis stroke="#64748b" fontSize={11} />
        <Tooltip
          contentStyle={{
            background: "#151d2e",
            border: "1px solid #1e2a3d",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Area
          type="monotone"
          dataKey="attacks"
          stroke="#f43f5e"
          fill="#f43f5e33"
          name="Suspicious"
        />
        <Area
          type="monotone"
          dataKey="benign"
          stroke="#06b6d4"
          fill="#06b6d422"
          name="Normal"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
