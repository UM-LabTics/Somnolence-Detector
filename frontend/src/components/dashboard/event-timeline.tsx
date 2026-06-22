"use client";

import { useMemo } from "react";
import type { DeviceResponse, TimelineEvent } from "@/lib/types";
import { cn, formatAlertType, formatTime } from "@/lib/utils";

const SEV_TONE: Record<string, string> = {
  HIGH: "text-critical",
  MEDIUM: "text-warn",
  LOW: "text-info",
};

interface EventTimelineProps {
  events: TimelineEvent[] | null;
  devices: DeviceResponse[] | null;
  className?: string;
}

export function EventTimeline({
  events,
  devices,
  className,
}: EventTimelineProps) {
  const deviceName = useMemo(() => {
    const map = new Map(devices?.map((d) => [d.id, d.name]) ?? []);
    return (id: string) => map.get(id) ?? id.slice(0, 6);
  }, [devices]);

  const items = (events ?? []).slice(0, 60);

  return (
    <div
      className={cn(
        "flex flex-col bg-card/60 ring-1 ring-border",
        className
      )}
    >
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <span className="mono-label">Event Log · realtime</span>
        <span className="mono-label tabular">{items.length} rows</span>
      </div>

      {items.length === 0 ? (
        <div className="mono-label flex flex-1 items-center justify-center py-12">
          Sin eventos registrados
        </div>
      ) : (
        <div className="relative max-h-[440px] overflow-y-auto">
          <table className="w-full font-mono tabular text-xs">
            <tbody>
              {items.map((e, i) => {
                const isAlert = e.event_type === "alert";
                const sev =
                  isAlert && e.severity
                    ? SEV_TONE[e.severity]
                    : "text-muted-foreground";
                return (
                  <tr
                    key={`${e.timestamp}-${i}`}
                    className="border-b border-border/40 transition-colors last:border-0 hover:bg-accent/40"
                  >
                    <td className="whitespace-nowrap px-5 py-2 text-muted-foreground">
                      {formatTime(e.timestamp)}
                    </td>
                    <td className="px-2 py-2">
                      <span
                        className={cn(
                          "inline-block w-16 text-[0.6rem] font-semibold tracking-[0.2em]",
                          sev
                        )}
                      >
                        {isAlert ? e.severity ?? "ALERT" : "ENV"}
                      </span>
                    </td>
                    <td className="min-w-0 px-2 py-2 text-foreground/80">
                      {isAlert ? (
                        <span>
                          <span className="text-foreground">
                            {formatAlertType(e.alert_type ?? "")}
                          </span>
                          <span className="text-muted-foreground">
                            {" "}
                            · val {e.value?.toFixed(2) ?? "—"}
                          </span>
                        </span>
                      ) : (
                        <span className="text-muted-foreground">
                          {e.temperature?.toFixed(1)}°C ·{" "}
                          {e.humidity?.toFixed(0)}% ·{" "}
                          {Math.round(e.co2 ?? 0)} ppm
                        </span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-5 py-2 text-right text-muted-foreground">
                      {deviceName(e.device_id)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
