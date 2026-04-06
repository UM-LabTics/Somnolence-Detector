"use client";

import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AlertNotificationResponse } from "@/lib/types";
import { acknowledgeNotification } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface NotificationListProps {
  notifications: AlertNotificationResponse[] | null;
  onAcknowledge: () => void;
}

export function NotificationList({
  notifications,
  onAcknowledge,
}: NotificationListProps) {
  const pending = (notifications ?? []).filter((n) => !n.acknowledged);

  const handleAcknowledge = async (id: string) => {
    await acknowledgeNotification(id);
    onAcknowledge();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bell className="h-5 w-5" />
          Notificaciones
          {pending.length > 0 && (
            <span className="rounded-full bg-[var(--severity-high)] px-2 py-0.5 text-xs text-white">
              {pending.length}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {pending.length === 0 ? (
          <p className="text-muted-foreground text-sm py-4 text-center">
            No hay notificaciones pendientes
          </p>
        ) : (
          <div className="space-y-3">
            {pending.map((n) => (
              <div
                key={n.id}
                className="flex items-center justify-between rounded-md border border-[var(--severity-high)]/30 bg-[var(--severity-high)]/5 p-3"
              >
                <div>
                  <p className="font-medium text-sm">
                    {n.alert_count} alertas en {n.time_window_minutes} min
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Dispositivo: {n.device_id.slice(0, 8)}...
                    {" · "}
                    {formatDateTime(n.created_at)}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleAcknowledge(n.id)}
                >
                  Reconocer
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
