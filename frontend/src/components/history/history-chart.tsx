"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { HistoryDataPoint } from "@/lib/types";
import { formatPeriod } from "@/lib/utils";

interface HistoryChartProps {
  data: HistoryDataPoint[];
  groupBy: string;
}

export function HistoryChart({ data, groupBy }: HistoryChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    periodLabel: formatPeriod(d.period, groupBy),
  }));

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Datos Historicos</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm py-8 text-center">
            Sin datos para el periodo seleccionado
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Datos Historicos</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis dataKey="periodLabel" tick={{ fontSize: 12 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 12 }} tickFormatter={(v) => Number(v).toFixed(1)} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--card)",
                border: "1px solid var(--border)",
                color: "var(--card-foreground)",
                borderRadius: "var(--radius)",
              }}
              formatter={(value: number, name: string) => {
                if (name === "Alertas") return [value, name];
                if (name === "CO₂ (ppm)") return [Math.round(value), name];
                return [Number(value).toFixed(1), name];
              }}
            />
            <Legend />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="avg_temperature"
              stroke="var(--chart-1)"
              dot={false}
              strokeWidth={2}
              name="Temperatura (°C)"
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="avg_humidity"
              stroke="var(--chart-2)"
              dot={false}
              strokeWidth={2}
              name="Humedad (%)"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="avg_co2"
              stroke="var(--chart-3)"
              dot={false}
              strokeWidth={2}
              name="CO₂ (ppm)"
            />
            <Bar
              yAxisId="right"
              dataKey="alert_count"
              fill="var(--chart-4)"
              opacity={0.6}
              radius={[4, 4, 0, 0]}
              name="Alertas"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
