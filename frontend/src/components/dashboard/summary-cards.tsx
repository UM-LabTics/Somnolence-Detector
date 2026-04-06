"use client";

import { AlertTriangle, Droplets, Thermometer, Wind } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardSummary } from "@/lib/types";

interface SummaryCardsProps {
  data: DashboardSummary | null;
}

export function SummaryCards({ data }: SummaryCardsProps) {
  const env = data?.environmental;

  const cards = [
    {
      title: "Temperatura",
      value: env?.avg_temperature != null ? `${env.avg_temperature.toFixed(1)}°C` : "---",
      icon: Thermometer,
      color: "text-[var(--chart-1)]",
    },
    {
      title: "Humedad",
      value: env?.avg_humidity != null ? `${env.avg_humidity.toFixed(1)}%` : "---",
      icon: Droplets,
      color: "text-[var(--chart-2)]",
    },
    {
      title: "CO₂",
      value: env?.avg_co2 != null ? `${Math.round(env.avg_co2)} ppm` : "---",
      icon: Wind,
      color: "text-[var(--chart-3)]",
    },
    {
      title: "Alertas (24h)",
      value: data?.total_alerts?.toString() ?? "---",
      icon: AlertTriangle,
      color: data?.total_alerts ? "text-[var(--chart-4)]" : "text-muted-foreground",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map(({ title, value, icon: Icon, color }) => (
        <Card key={title}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {title}
            </CardTitle>
            <Icon className={`h-4 w-4 ${color}`} />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
