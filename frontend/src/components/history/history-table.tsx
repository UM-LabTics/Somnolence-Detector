"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { HistoryDataPoint } from "@/lib/types";
import { formatPeriod } from "@/lib/utils";

interface HistoryTableProps {
  data: HistoryDataPoint[];
  groupBy: string;
}

export function HistoryTable({ data, groupBy }: HistoryTableProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Tabla de Datos</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="text-muted-foreground text-sm py-4 text-center">
            Sin datos
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Periodo</TableHead>
                <TableHead className="text-right">Temp (°C)</TableHead>
                <TableHead className="text-right">Humedad (%)</TableHead>
                <TableHead className="text-right">CO₂ (ppm)</TableHead>
                <TableHead className="text-right">Alertas</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((row) => (
                <TableRow key={row.period}>
                  <TableCell className="font-mono text-sm">
                    {formatPeriod(row.period, groupBy)}
                  </TableCell>
                  <TableCell className="text-right">
                    {row.avg_temperature?.toFixed(1) ?? "---"}
                  </TableCell>
                  <TableCell className="text-right">
                    {row.avg_humidity?.toFixed(1) ?? "---"}
                  </TableCell>
                  <TableCell className="text-right">
                    {row.avg_co2 != null ? Math.round(row.avg_co2) : "---"}
                  </TableCell>
                  <TableCell className="text-right">{row.alert_count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
