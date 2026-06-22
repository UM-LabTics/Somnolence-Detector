"use client";

import { useMemo } from "react";
import type {
  AlertNotificationResponse,
  DeviceResponse,
  TimelineEvent,
} from "@/lib/types";
import { cn, parseUtc } from "@/lib/utils";
import { useNow } from "@/hooks/use-now";

type Status = "nominal" | "elevated" | "critical" | "unknown";

const STATUS_CONFIG: Record<
  Status,
  { label: string; tone: string; dot: string; description: string }
> = {
  nominal: {
    label: "NOMINAL",
    tone: "text-ok",
    dot: "bg-ok text-ok",
    description: "Todos los sistemas operativos · sin eventos recientes",
  },
  elevated: {
    label: "ELEVADO",
    tone: "text-warn",
    dot: "bg-warn text-warn",
    description: "Actividad de alerta detectada · supervisar",
  },
  critical: {
    label: "CRÍTICO",
    tone: "text-critical",
    dot: "bg-critical text-critical",
    description: "Severidad alta en los últimos 5 minutos",
  },
  unknown: {
    label: "OFFLINE",
    tone: "text-muted-foreground",
    dot: "bg-muted-foreground text-muted-foreground",
    description: "Esperando telemetría del backend…",
  },
};

interface FleetStatusProps {
  timeline: TimelineEvent[] | null;
  devices: DeviceResponse[] | null;
  notifications: AlertNotificationResponse[] | null;
  className?: string;
}

export function FleetStatus({
  timeline,
  devices,
  notifications,
  className,
}: FleetStatusProps) {
  const now = useNow(30_000);

  const metrics = useMemo(() => {
    if (!timeline) {
      return {
        status: "unknown" as Status,
        alerts15: 0,
        criticals5: 0,
        online: 0,
        total: 0,
        pending: 0,
      };
    }

    const FIVE_MIN = 5 * 60 * 1000;
    const FIFTEEN_MIN = 15 * 60 * 1000;
    const TEN_MIN = 10 * 60 * 1000;

    let alerts15 = 0;
    let criticals5 = 0;
    for (const e of timeline) {
      if (e.event_type !== "alert") continue;
      const age = now - parseUtc(e.timestamp).getTime();
      if (age <= FIFTEEN_MIN) alerts15++;
      if (age <= FIVE_MIN && e.severity === "HIGH") criticals5++;
    }

    const pending = (notifications ?? []).filter((n) => !n.acknowledged)
      .length;
    const total = devices?.length ?? 0;
    const online = (devices ?? []).filter((d) => {
      if (!d.is_active || !d.last_seen_at) return false;
      return now - parseUtc(d.last_seen_at).getTime() <= TEN_MIN;
    }).length;

    let status: Status = "nominal";
    if (criticals5 > 0) status = "critical";
    else if (alerts15 > 0 || pending > 0) status = "elevated";

    return { status, alerts15, criticals5, online, total, pending };
  }, [timeline, devices, notifications, now]);

  const cfg = STATUS_CONFIG[metrics.status];

  return (
    <div
      className={cn(
        "corner-ticks relative flex flex-col gap-6 bg-card/60 p-6 ring-1 ring-border",
        metrics.status === "critical" && "ring-critical/40",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="mono-label">Fleet Status</span>
        <span className="mono-label tabular">
          {now ? new Date(now).toISOString().slice(0, 10) : "----"}
        </span>
      </div>

      <div className="flex items-start gap-5">
        <div className="flex flex-col items-center gap-1 pt-3">
          <span
            className={cn(
              "block h-3 w-3 rounded-full animate-pulse-dot",
              cfg.dot
            )}
          />
          <span className="mono-label text-[0.55rem] opacity-60 writing-mode-vertical">
            STS
          </span>
        </div>
        <div className="flex-1">
          <div
            className={cn(
              "font-heading leading-none tracking-tight text-6xl md:text-7xl",
              cfg.tone
            )}
          >
            {cfg.label}
          </div>
          <p className="mt-4 max-w-md text-sm text-muted-foreground">
            {cfg.description}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-x-4 border-t border-border pt-5">
        <Metric label="Online" value={`${metrics.online}/${metrics.total || "—"}`} />
        <Metric label="Alert · 15m" value={metrics.alerts15} />
        <Metric
          label="High · 5m"
          value={metrics.criticals5}
          tone={metrics.criticals5 ? "text-critical" : undefined}
        />
        <Metric
          label="Pending"
          value={metrics.pending}
          tone={metrics.pending ? "text-warn" : undefined}
        />
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string;
  tone?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="mono-label">{label}</span>
      <span
        className={cn(
          "font-mono tabular text-2xl leading-tight text-foreground",
          tone
        )}
      >
        {value}
      </span>
    </div>
  );
}
