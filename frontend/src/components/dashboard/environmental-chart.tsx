"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TimelineEvent } from "@/lib/types";
import { formatTime } from "@/lib/utils";

interface EnvironmentalChartProps {
  events: TimelineEvent[] | null;
}

export function EnvironmentalChart({ events }: EnvironmentalChartProps) {
  const envData = (events ?? [])
    .filter((e) => e.event_type === "environmental")
    .slice()
    .reverse()
    .map((e) => ({
      time: formatTime(e.timestamp),
      temp: e.temperature,
      hum: e.humidity,
      co2: e.co2,
    }));

  return (
    <section className="bg-card/40 ring-1 ring-border">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-3">
        <div className="flex flex-wrap items-center gap-5">
          <span className="mono-label">Cabin Telemetry · 24h</span>
          <div className="flex items-center gap-4 font-mono text-[0.68rem] text-muted-foreground">
            <LegendItem color="var(--chart-1)" label="T °C" />
            <LegendItem color="var(--chart-2)" label="RH %" />
            <LegendItem color="var(--chart-3)" label="CO₂ ppm" />
          </div>
        </div>
        <span className="mono-label tabular">{envData.length} samples</span>
      </div>
      <div className="px-3 py-4">
        {envData.length === 0 ? (
          <div className="mono-label flex h-[260px] items-center justify-center">
            Sin datos ambientales
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart
              data={envData}
              margin={{ top: 12, right: 18, left: 0, bottom: 0 }}
            >
              <CartesianGrid
                stroke="var(--border)"
                strokeDasharray="0"
                vertical={false}
              />
              <XAxis
                dataKey="time"
                tick={{
                  fontSize: 10,
                  fontFamily: "var(--font-plex-mono)",
                  fill: "var(--muted-foreground)",
                }}
                axisLine={{ stroke: "var(--border)" }}
                tickLine={{ stroke: "var(--border)" }}
                minTickGap={40}
              />
              <YAxis
                yAxisId="left"
                tick={{
                  fontSize: 10,
                  fontFamily: "var(--font-plex-mono)",
                  fill: "var(--muted-foreground)",
                }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{
                  fontSize: 10,
                  fontFamily: "var(--font-plex-mono)",
                  fill: "var(--muted-foreground)",
                }}
                axisLine={false}
                tickLine={false}
                width={50}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--popover)",
                  border: "1px solid var(--border)",
                  borderRadius: "2px",
                  fontFamily: "var(--font-plex-mono)",
                  fontSize: "11px",
                  color: "var(--popover-foreground)",
                }}
                labelStyle={{ color: "var(--muted-foreground)" }}
                cursor={{ stroke: "var(--primary)", strokeWidth: 1, strokeDasharray: "2 3" }}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="temp"
                name="T °C"
                stroke="var(--chart-1)"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="hum"
                name="RH %"
                stroke="var(--chart-2)"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="co2"
                name="CO₂ ppm"
                stroke="var(--chart-3)"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        className="h-2 w-2"
        style={{ background: color, boxShadow: `0 0 6px ${color}` }}
      />
      {label}
    </span>
  );
}
