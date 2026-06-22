"use client";

import { AlertTriangle, Droplets, Thermometer, Wind } from "lucide-react";
import type { DashboardSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

interface EnvStripProps {
  data: DashboardSummary | null;
}

function formatAge(ts: string | null): string {
  if (!ts) return "";
  const diffMs = Date.now() - new Date(ts).getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "ahora";
  if (diffMin < 60) return `hace ${diffMin}m`;
  return `hace ${Math.floor(diffMin / 60)}h`;
}

export function EnvStrip({ data }: EnvStripProps) {
  const latest = data?.latest_environmental;
  const avg = data?.environmental;
  const latestTs = latest?.timestamp ?? null;

  const entries = [
    {
      label: "Temp",
      value: latest?.temperature != null ? latest.temperature.toFixed(1) : "—",
      avg: avg?.avg_temperature != null ? avg.avg_temperature.toFixed(1) : null,
      unit: "°C",
      icon: Thermometer,
      tone: "text-chart-1",
    },
    {
      label: "Humedad",
      value: latest?.humidity != null ? latest.humidity.toFixed(0) : "—",
      avg: avg?.avg_humidity != null ? avg.avg_humidity.toFixed(0) : null,
      unit: "% RH",
      icon: Droplets,
      tone: "text-chart-2",
    },
    {
      label: "CO₂",
      value: latest?.co2 != null ? Math.round(latest.co2).toString() : "—",
      avg: avg?.avg_co2 != null ? Math.round(avg.avg_co2).toString() : null,
      unit: "ppm",
      icon: Wind,
      tone: "text-chart-3",
    },
    {
      label: "Alertas · 24h",
      value: data?.total_alerts != null ? data.total_alerts.toString() : "—",
      avg: null,
      unit: "evt",
      icon: AlertTriangle,
      tone: data?.total_alerts ? "text-critical" : "text-muted-foreground",
    },
  ];

  return (
    <section>
      <div className="flex items-center justify-between pb-2">
        <span className="mono-label">
          Cabin Environment · último
          {latestTs && (
            <span className="ml-2 opacity-60">{formatAge(latestTs)}</span>
          )}
        </span>
        <span className="mono-label tabular">{entries.length} channels</span>
      </div>
      <div className="grid grid-cols-2 divide-x divide-border border border-border bg-card/40 md:grid-cols-4">
        {entries.map((e, idx) => (
          <div
            key={e.label}
            className="relative flex items-center gap-4 px-5 py-4"
          >
            <e.icon className={cn("h-4 w-4 shrink-0", e.tone)} />
            <div className="flex min-w-0 flex-col leading-tight">
              <span className="mono-label">{e.label}</span>
              <span className="font-mono tabular text-2xl text-foreground">
                {e.value}
                <span className="ml-1.5 text-xs text-muted-foreground">
                  {e.unit}
                </span>
              </span>
              {e.avg != null && (
                <span className="font-mono text-[0.6rem] text-muted-foreground opacity-60">
                  avg 24h: {e.avg} {e.unit}
                </span>
              )}
            </div>
            <span className="mono-label absolute right-2 top-2 text-[0.5rem] opacity-40">
              CH·{String(idx + 1).padStart(2, "0")}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
