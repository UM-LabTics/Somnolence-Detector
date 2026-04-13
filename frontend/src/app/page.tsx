"use client";

import { useApi } from "@/hooks/use-api";
import {
  getDashboardSummary,
  getDevices,
  getNotifications,
  getTimeline,
} from "@/lib/api";
import type {
  AlertNotificationResponse,
  DashboardSummary,
  DeviceResponse,
  TimelineEvent,
} from "@/lib/types";
import { ActiveAlerts } from "@/components/dashboard/active-alerts";
import { AlertsByTypeChart } from "@/components/dashboard/alerts-by-type-chart";
import { EnvStrip } from "@/components/dashboard/env-strip";
import { EnvironmentalChart } from "@/components/dashboard/environmental-chart";
import { EventTimeline } from "@/components/dashboard/event-timeline";
import { FleetStatus } from "@/components/dashboard/fleet-status";
import { NotificationList } from "@/components/dashboard/notification-list";

const REFRESH_MS = 15_000;

export default function DashboardPage() {
  const summary = useApi<DashboardSummary>(() => getDashboardSummary(), {
    refreshInterval: REFRESH_MS,
  });
  const timeline = useApi<TimelineEvent[]>(() => getTimeline(), {
    refreshInterval: REFRESH_MS,
  });
  const notifications = useApi<AlertNotificationResponse[]>(
    () => getNotifications({ acknowledged: false }),
    { refreshInterval: REFRESH_MS }
  );
  const devices = useApi<DeviceResponse[]>(() => getDevices(), {
    refreshInterval: REFRESH_MS * 2,
  });

  const anyError =
    summary.error ?? timeline.error ?? notifications.error ?? devices.error;

  return (
    <div className="relative mx-auto flex max-w-[1400px] flex-col gap-6 px-6 py-8">
      <div className="flex items-end justify-between gap-6 border-b border-border pb-5">
        <div>
          <div className="mono-label">Sector 01 · Panel de Control</div>
          <h1 className="mt-1 font-heading text-4xl leading-none text-foreground md:text-5xl">
            Visión general de la flota
          </h1>
        </div>
        <div className="hidden items-center gap-6 font-mono text-xs text-muted-foreground md:flex">
          <div className="flex flex-col items-end leading-tight">
            <span className="mono-label">Refresh</span>
            <span className="tabular text-foreground">
              {REFRESH_MS / 1000}s
            </span>
          </div>
          <div className="flex flex-col items-end leading-tight">
            <span className="mono-label">Source</span>
            <span className="tabular text-foreground">api/v1</span>
          </div>
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-5">
        <FleetStatus
          className="lg:col-span-2"
          timeline={timeline.data}
          devices={devices.data}
          notifications={notifications.data}
        />
        <ActiveAlerts
          className="lg:col-span-3"
          timeline={timeline.data}
          devices={devices.data}
        />
      </section>

      <EnvStrip data={summary.data} />

      <section className="grid gap-4 lg:grid-cols-5">
        <AlertsByTypeChart
          className="lg:col-span-2"
          data={summary.data?.alert_counts_by_type ?? null}
          total={summary.data?.total_alerts ?? 0}
        />
        <EventTimeline
          className="lg:col-span-3"
          events={timeline.data}
          devices={devices.data}
        />
      </section>

      <EnvironmentalChart events={timeline.data} />

      <NotificationList
        notifications={notifications.data}
        devices={devices.data}
        onAcknowledge={notifications.refresh}
      />

      {anyError && (
        <div className="border border-critical/40 bg-critical/10 px-4 py-3">
          <span className="mono-label text-critical">Error · </span>
          <span className="font-mono text-xs text-critical">{anyError}</span>
        </div>
      )}
    </div>
  );
}
