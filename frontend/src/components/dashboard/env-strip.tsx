"use client";

import { AlertTriangle, Droplets, Thermometer, Wind } from "lucide-react";
import type { DashboardSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

interface EnvStripProps {
  data: DashboardSummary | null;
}

export function EnvStrip({ data }: EnvStripProps) {
  const env = data?.environmental;

  const entries = [
    {
      label: "Temp",
      value:
        env?.avg_temperature != null ? env.avg_temperature.toFixed(1) : "—",
      unit: "°C",
      icon: Thermometer,
      tone: "text-chart-1",
    },
    {
      label: "Humedad",
      value: env?.avg_humidity != null ? env.avg_humidity.toFixed(0) : "—",
      unit: "% RH",
      icon: Droplets,
      tone: "text-chart-2",
    },
    {
      label: "CO₂",
      value: env?.avg_co2 != null ? Math.round(env.avg_co2).toString() : "—",
      unit: "ppm",
      icon: Wind,
      tone: "text-chart-3",
    },
    {
      label: "Alertas · 24h",
      value:
        data?.total_alerts != null ? data.total_alerts.toString() : "—",
      unit: "evt",
      icon: AlertTriangle,
      tone: data?.total_alerts ? "text-critical" : "text-muted-foreground",
    },
  ];

  return (
    <section>
      <div className="flex items-center justify-between pb-2">
        <span className="mono-label">Cabin Environment · avg 24h</span>
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
