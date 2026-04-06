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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AlertCountByType } from "@/lib/types";
import { formatAlertType } from "@/lib/utils";

interface AlertsByTypeChartProps {
  data: AlertCountByType[] | null;
}

export function AlertsByTypeChart({ data }: AlertsByTypeChartProps) {
  const chartData = (data ?? []).map((d) => ({
    type: formatAlertType(d.alert_type),
    count: d.count,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Alertas por Tipo (24h)</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Sin alertas
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis dataKey="type" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--card)",
                  border: "1px solid var(--border)",
                  color: "var(--card-foreground)",
                  borderRadius: "var(--radius)",
                }}
              />
              <Bar
                dataKey="count"
                fill="var(--chart-4)"
                radius={[4, 4, 0, 0]}
                name="Alertas"
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
