"use client";

import { useMemo } from "react";
import { Bell, Check } from "lucide-react";
import type {
  AlertNotificationResponse,
  DeviceResponse,
} from "@/lib/types";
import { acknowledgeNotification } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface NotificationListProps {
  notifications: AlertNotificationResponse[] | null;
  devices: DeviceResponse[] | null;
  onAcknowledge: () => void;
}

export function NotificationList({
  notifications,
  devices,
  onAcknowledge,
}: NotificationListProps) {
  const pending = (notifications ?? []).filter((n) => !n.acknowledged);
  const deviceName = useMemo(() => {
    const map = new Map(devices?.map((d) => [d.id, d.name]) ?? []);
    return (id: string) => map.get(id) ?? id.slice(0, 8);
  }, [devices]);

  if (pending.length === 0) return null;

  const handleAck = async (id: string) => {
    await acknowledgeNotification(id);
    onAcknowledge();
  };

  return (
    <section className="relative overflow-hidden bg-card/40 ring-1 ring-critical/35">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-critical to-transparent animate-sweep" />

      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <Bell className="h-3.5 w-3.5 text-critical animate-blink" />
          <span className="mono-label text-critical">
            Notificaciones activas
          </span>
        </div>
        <span className="font-mono tabular text-xs text-critical">
          {pending.length} pending
        </span>
      </div>

      <ul className="divide-y divide-border">
        {pending.map((n) => (
          <li
            key={n.id}
            className="grid grid-cols-[auto_1fr_auto] items-center gap-4 px-6 py-4"
          >
            <div className="flex h-10 w-10 items-center justify-center bg-critical/10 ring-1 ring-critical/40">
              <span className="font-mono tabular text-sm font-semibold text-critical">
                {n.alert_count}
              </span>
            </div>
            <div className="min-w-0">
              <div className="text-sm text-foreground">
                <span className="font-medium">{n.alert_count}</span>
                <span className="text-muted-foreground"> alertas en </span>
                <span className="font-mono tabular">
                  {n.time_window_minutes} min
                </span>
              </div>
              <div className="mt-0.5 font-mono tabular text-xs text-muted-foreground">
                {deviceName(n.device_id)} · {formatDateTime(n.created_at)}
              </div>
            </div>
            <button
              onClick={() => handleAck(n.id)}
              className="flex items-center gap-2 border border-border px-3 py-1.5 font-mono text-xs tracking-[0.18em] text-foreground transition-colors hover:border-primary hover:bg-primary hover:text-primary-foreground"
            >
              <Check className="h-3 w-3" />
              <span>RECONOCER</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
