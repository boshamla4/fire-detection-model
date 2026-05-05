"use client";

import type { DetectionEvent } from "@/lib/types";
import { BarChart, Bar, XAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface Props {
  events: DetectionEvent[];
}

export default function StatsPanel({ events }: Props) {
  // Confidence histogram buckets: 0.4-0.5, 0.5-0.6, ..., 0.9-1.0
  const buckets = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9];
  const histData = buckets.map((lo) => ({
    range: `${(lo * 100).toFixed(0)}`,
    count: events.filter((e) => e.confidence >= lo && e.confidence < lo + 0.1).length,
  }));

  const avgConf =
    events.length > 0
      ? (events.reduce((s, e) => s + e.confidence, 0) / events.length) * 100
      : 0;

  return (
    <div>
      <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Confidence Distribution
      </h2>
      <p className="text-xs text-slate-500 mb-2">
        Avg:{" "}
        <span className="text-slate-300 font-medium">{avgConf.toFixed(1)}%</span>
      </p>
      <ResponsiveContainer width="100%" height={80}>
        <BarChart data={histData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
          <XAxis
            dataKey="range"
            tick={{ fontSize: 10, fill: "#64748b" }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 6 }}
            labelStyle={{ color: "#94a3b8", fontSize: 11 }}
            itemStyle={{ color: "#f97316", fontSize: 11 }}
            formatter={(val: number) => [val, "events"]}
          />
          <Bar dataKey="count" radius={[3, 3, 0, 0]}>
            {histData.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.count > 0 ? "#f97316" : "#1e293b"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
