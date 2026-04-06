"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AlertNotificationResponse, DeviceResponse } from "@/lib/types";
import { formatRelativeTime } from "@/lib/utils";

interface DeviceListProps {
  devices: DeviceResponse[];
  notifications: AlertNotificationResponse[];
}

export function DeviceList({ devices, notifications }: DeviceListProps) {
  if (devices.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-8">
        No hay dispositivos registrados
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {devices.map((device) => {
        const pendingCount = notifications.filter(
          (n) => n.device_id === device.id && !n.acknowledged
        ).length;

        return (
          <Card key={device.id}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{device.name}</CardTitle>
                <Badge
                  variant={device.is_active ? "default" : "secondary"}
                  className={
                    device.is_active
                      ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                      : ""
                  }
                >
                  {device.is_active ? "Activo" : "Inactivo"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>Ultima vez: {formatRelativeTime(device.last_seen_at)}</p>
              <p className="font-mono text-xs" title={device.id}>
                ID: {device.id.slice(0, 8)}...
              </p>
              {pendingCount > 0 && (
                <p className="text-[var(--severity-high)] font-medium">
                  {pendingCount} notificacion{pendingCount > 1 ? "es" : ""}{" "}
                  pendiente{pendingCount > 1 ? "s" : ""}
                </p>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
