"use client";

import { useApi } from "@/hooks/use-api";
import { getDashboardSummary, getNotifications, getTimeline } from "@/lib/api";
import type {
  AlertNotificationResponse,
  DashboardSummary,
  TimelineEvent,
} from "@/lib/types";
import { SummaryCards } from "@/components/dashboard/summary-cards";
import { EnvironmentalChart } from "@/components/dashboard/environmental-chart";
import { AlertsByTypeChart } from "@/components/dashboard/alerts-by-type-chart";
import { EventTimeline } from "@/components/dashboard/event-timeline";
import { NotificationList } from "@/components/dashboard/notification-list";

const REFRESH_MS = 30000;

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

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4">
      <SummaryCards data={summary.data} />

      <EnvironmentalChart events={timeline.data} />

      <div className="grid gap-6 lg:grid-cols-2">
        <AlertsByTypeChart data={summary.data?.alert_counts_by_type ?? null} />
        <EventTimeline events={timeline.data} />
      </div>

      <NotificationList
        notifications={notifications.data}
        onAcknowledge={notifications.refresh}
      />
    </div>
  );
}
