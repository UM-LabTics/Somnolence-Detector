"use client";

import { AlertTriangle, ThermometerSun } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TimelineEvent } from "@/lib/types";
import { formatAlertType, formatTime } from "@/lib/utils";

interface EventTimelineProps {
  events: TimelineEvent[] | null;
}

const SEVERITY_STYLES: Record<string, string> = {
  LOW: "bg-[var(--severity-low)] text-foreground",
  MEDIUM: "bg-[var(--severity-medium)] text-foreground",
  HIGH: "bg-[var(--severity-high)] text-white",
};

export function EventTimeline({ events }: EventTimelineProps) {
  const items = events ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Linea de Tiempo</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Sin eventos
          </p>
        ) : (
          <div className="max-h-[400px] space-y-2 overflow-y-auto pr-2">
            {items.slice(0, 50).map((event, i) => (
              <div
                key={`${event.timestamp}-${i}`}
                className="flex items-start gap-3 rounded-md border p-2 text-sm"
              >
                {event.event_type === "alert" ? (
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--chart-4)]" />
                ) : (
                  <ThermometerSun className="mt-0.5 h-4 w-4 shrink-0 text-[var(--chart-1)]" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground font-mono text-xs">
                      {formatTime(event.timestamp)}
                    </span>
                    {event.event_type === "alert" && event.severity && (
                      <Badge
                        className={SEVERITY_STYLES[event.severity] ?? ""}
                        variant="secondary"
                      >
                        {event.severity}
                      </Badge>
                    )}
                  </div>
                  {event.event_type === "alert" ? (
                    <p>
                      {formatAlertType(event.alert_type ?? "")}{" "}
                      <span className="text-muted-foreground">
                        (valor: {event.value?.toFixed(2)})
                      </span>
                    </p>
                  ) : (
                    <p className="text-muted-foreground">
                      {event.temperature != null && `${event.temperature.toFixed(1)}°C `}
                      {event.humidity != null && `${event.humidity.toFixed(1)}% `}
                      {event.co2 != null && `${Math.round(event.co2)} ppm`}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
