"use client";

import { useApi } from "@/hooks/use-api";
import { getDevices, getNotifications } from "@/lib/api";
import type { AlertNotificationResponse, DeviceResponse } from "@/lib/types";
import { DeviceList } from "@/components/devices/device-list";

const REFRESH_MS = 30000;

export default function DevicesPage() {
  const devices = useApi<DeviceResponse[]>(() => getDevices(), {
    refreshInterval: REFRESH_MS,
  });

  const notifications = useApi<AlertNotificationResponse[]>(
    () => getNotifications(),
    { refreshInterval: REFRESH_MS }
  );

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4">
      <h2 className="text-2xl font-semibold tracking-tight">Dispositivos</h2>

      {devices.isLoading && !devices.data ? (
        <p className="text-muted-foreground text-center py-8">Cargando...</p>
      ) : devices.error ? (
        <p className="text-destructive text-center py-8">
          Error: {devices.error}
        </p>
      ) : (
        <DeviceList
          devices={devices.data ?? []}
          notifications={notifications.data ?? []}
        />
      )}
    </div>
  );
}
