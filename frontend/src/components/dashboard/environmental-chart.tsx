"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TimelineEvent } from "@/lib/types";
import { formatTime } from "@/lib/utils";

interface EnvironmentalChartProps {
  events: TimelineEvent[] | null;
}

export function EnvironmentalChart({ events }: EnvironmentalChartProps) {
  const envData = (events ?? [])
    .filter((e) => e.event_type === "environmental")
    .reverse()
    .map((e) => ({
      time: formatTime(e.timestamp),
      Temperatura: e.temperature,
      Humedad: e.humidity,
      CO2: e.co2,
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Condiciones Ambientales (24h)</CardTitle>
      </CardHeader>
      <CardContent>
        {envData.length === 0 ? (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Sin datos ambientales
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={envData}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--card)",
                  border: "1px solid var(--border)",
                  color: "var(--card-foreground)",
                  borderRadius: "var(--radius)",
                }}
              />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="Temperatura"
                stroke="var(--chart-1)"
                dot={false}
                strokeWidth={2}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="Humedad"
                stroke="var(--chart-2)"
                dot={false}
                strokeWidth={2}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="CO2"
                stroke="var(--chart-3)"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
