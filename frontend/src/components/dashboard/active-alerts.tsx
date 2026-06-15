"use client";

import { useMemo } from "react";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import type { DeviceResponse, TimelineEvent } from "@/lib/types";
import {
  cn,
  formatAlertType,
  formatRelativeTime,
} from "@/lib/utils";
import { useNow } from "@/hooks/use-now";

const SEVERITY_STYLE: Record<
  string,
  { ring: string; label: string; text: string; dot: string }
> = {
  HIGH: {
    ring: "ring-critical/40",
    label: "CRITICAL",
    text: "text-critical",
    dot: "bg-critical text-critical",
  },
  MEDIUM: {
    ring: "ring-warn/30",
    label: "WARNING",
    text: "text-warn",
    dot: "bg-warn text-warn",
  },
  LOW: {
    ring: "ring-info/25",
    label: "NOTICE",
    text: "text-info",
    dot: "bg-info text-info",
  },
};

interface ActiveAlertsProps {
  timeline: TimelineEvent[] | null;
  devices: DeviceResponse[] | null;
  className?: string;
}

export function ActiveAlerts({
  timeline,
  devices,
  className,
}: ActiveAlertsProps) {
  const now = useNow(30_000);

  const recent = useMemo(() => {
    if (!timeline) return [];
    const windowMs = 15 * 60 * 1000;
    const map = new Map(devices?.map((d) => [d.id, d.name]) ?? []);
    return timeline
      .filter(
        (e) =>
          e.event_type === "alert" &&
          now - new Date(e.timestamp).getTime() <= windowMs
      )
      .slice(0, 8)
      .map((e) => ({
        ...e,
        deviceName: map.get(e.device_id) ?? e.device_id.slice(0, 8),
      }));
  }, [timeline, devices, now]);

  return (
    <div
      className={cn(
        "relative flex flex-col bg-card/60 ring-1 ring-border",
        className
      )}
    >
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <span className="mono-label">Active Alerts · 15m</span>
        <div className="flex items-center gap-2">
          <span className="mono-label">Stream</span>
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full animate-pulse-dot",
              recent.length
                ? "bg-critical text-critical"
                : "bg-ok text-ok"
            )}
          />
        </div>
      </div>

      {recent.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-12 text-center">
          <ShieldCheck className="h-8 w-8 text-ok" />
          <div className="font-heading text-2xl text-ok">
            Sin alertas activas
          </div>
          <div className="mono-label">
            Sin eventos detectados en los últimos 15 minutos
          </div>
        </div>
      ) : (
        <ol className="divide-y divide-border">
          {recent.map((e, i) => {
            const sev =
              SEVERITY_STYLE[e.severity ?? "LOW"] ?? SEVERITY_STYLE.LOW;
            return (
              <li
                key={`${e.timestamp}-${i}`}
                className="relative grid grid-cols-[auto_1fr_auto] items-center gap-4 px-6 py-3"
                style={{
                  animation: `fade-in-up 0.45s ease-out ${i * 0.04}s both`,
                }}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center ring-1",
                    sev.ring
                  )}
                >
                  <AlertTriangle className={cn("h-4 w-4", sev.text)} />
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "font-mono text-[0.6rem] font-semibold tracking-[0.22em]",
                        sev.text
                      )}
                    >
                      {sev.label}
                    </span>
                    <span className="text-muted-foreground text-xs">·</span>
                    <span className="truncate text-sm font-medium text-foreground">
                      {formatAlertType(e.alert_type ?? "")}
                    </span>
                  </div>
                  <div className="mt-0.5 font-mono tabular text-xs text-muted-foreground">
                    <span className="text-foreground/80">{e.deviceName}</span>
                    <span> · val {e.value?.toFixed(2) ?? "—"}</span>
                  </div>
                </div>

                <div className="text-right font-mono tabular text-xs text-muted-foreground">
                  {formatRelativeTime(e.timestamp)}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
