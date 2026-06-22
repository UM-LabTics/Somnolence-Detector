"use client";

import { useState } from "react";
import { AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";
import { useApi } from "@/hooks/use-api";
import { getAlerts } from "@/lib/api";
import type { AlertResponse, DeviceResponse } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn, formatAlertType, formatDateTime } from "@/lib/utils";

const SEVERITY_STYLE: Record<string, { label: string; text: string }> = {
  HIGH: { label: "CRÍTICO", text: "text-critical" },
  MEDIUM: { label: "ADVERTENCIA", text: "text-warn" },
  LOW: { label: "AVISO", text: "text-info" },
};

const LIMIT = 20;

interface AlertsHistoryTableProps {
  startDate: string;
  endDate: string;
  deviceId: string;
  devices: DeviceResponse[];
}

export function AlertsHistoryTable({
  startDate,
  endDate,
  deviceId,
  devices,
}: AlertsHistoryTableProps) {
  const [alertType, setAlertType] = useState("all");
  const [severity, setSeverity] = useState("all");
  const [skip, setSkip] = useState(0);

  const deviceMap = new Map(devices.map((d) => [d.id, d.name]));

  const alerts = useApi<AlertResponse[]>(
    () =>
      getAlerts({
        device_id: deviceId === "all" ? undefined : deviceId,
        alert_type: alertType === "all" ? undefined : alertType,
        severity: severity === "all" ? undefined : severity,
        start_date: startDate,
        end_date: endDate,
        skip,
        limit: LIMIT,
      }),
    { deps: [startDate, endDate, deviceId, alertType, severity, skip] }
  );

  function handleAlertTypeChange(val: string | null) {
    setAlertType(val ?? "all");
    setSkip(0);
  }

  function handleSeverityChange(val: string | null) {
    setSeverity(val ?? "all");
    setSkip(0);
  }

  const data = alerts.data ?? [];
  const hasPrev = skip > 0;
  const hasNext = data.length === LIMIT;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-warn" />
            Alertas Individuales
          </CardTitle>
          <div className="flex gap-2">
            <Select value={alertType} onValueChange={handleAlertTypeChange}>
              <SelectTrigger className="w-44 text-xs">
                <SelectValue placeholder="Tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los tipos</SelectItem>
                <SelectItem value="EYE_CLOSURE">Cierre de ojos</SelectItem>
                <SelectItem value="YAWN">Bostezo</SelectItem>
                <SelectItem value="HEAD_NOD">Cabeceo</SelectItem>
                <SelectItem value="PHONE_USE">Uso de celular</SelectItem>
              </SelectContent>
            </Select>
            <Select value={severity} onValueChange={handleSeverityChange}>
              <SelectTrigger className="w-40 text-xs">
                <SelectValue placeholder="Severidad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toda severidad</SelectItem>
                <SelectItem value="HIGH">Crítico</SelectItem>
                <SelectItem value="MEDIUM">Advertencia</SelectItem>
                <SelectItem value="LOW">Aviso</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {alerts.isLoading && !alerts.data ? (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Cargando...
          </p>
        ) : alerts.error ? (
          <p className="text-destructive text-sm py-8 text-center">
            Error: {alerts.error}
          </p>
        ) : data.length === 0 ? (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Sin alertas para el período seleccionado
          </p>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Severidad</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                  <TableHead className="text-right">Umbral</TableHead>
                  <TableHead>Dispositivo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((alert) => {
                  const sev =
                    SEVERITY_STYLE[alert.severity] ?? SEVERITY_STYLE.LOW;
                  return (
                    <TableRow key={alert.id}>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {formatDateTime(alert.timestamp)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatAlertType(alert.alert_type)}
                      </TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            "font-mono text-[0.6rem] font-semibold tracking-[0.18em]",
                            sev.text
                          )}
                        >
                          {sev.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {alert.value.toFixed(3)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs text-muted-foreground">
                        {alert.threshold.toFixed(3)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {deviceMap.get(alert.device_id) ??
                          alert.device_id.slice(0, 8)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>

            <div className="mt-4 flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {skip + 1}–{skip + data.length}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!hasPrev}
                  onClick={() => setSkip((s) => Math.max(0, s - LIMIT))}
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!hasNext}
                  onClick={() => setSkip((s) => s + LIMIT)}
                >
                  Siguiente
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
