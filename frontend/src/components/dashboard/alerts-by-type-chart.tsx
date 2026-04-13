"use client";

import type { AlertCountByType } from "@/lib/types";
import { cn, formatAlertType } from "@/lib/utils";

interface AlertsByTypeChartProps {
  data: AlertCountByType[] | null;
  total: number;
  className?: string;
}

const TYPE_META: Record<string, { tone: string; code: string }> = {
  EYE_CLOSURE: { tone: "bg-critical/85", code: "EYE" },
  YAWN: { tone: "bg-warn/85", code: "YWN" },
  HEAD_NOD: { tone: "bg-chart-1/85", code: "HED" },
  PHONE_USE: { tone: "bg-chart-5/85", code: "PHN" },
  PHONE_OBJECT: { tone: "bg-chart-4/85", code: "PHO" },
};

export function AlertsByTypeChart({
  data,
  total,
  className,
}: AlertsByTypeChartProps) {
  const items = data ?? [];
  const max = Math.max(1, ...items.map((i) => i.count));

  return (
    <div
      className={cn(
        "flex flex-col bg-card/60 ring-1 ring-border",
        className
      )}
    >
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <span className="mono-label">Alert Breakdown · 24h</span>
        <span className="mono-label tabular">{total} total</span>
      </div>

      {items.length === 0 ? (
        <div className="mono-label flex flex-1 items-center justify-center px-6 py-12">
          Sin alertas en el período
        </div>
      ) : (
        <ul className="flex flex-col gap-5 px-6 py-5">
          {items.map((item) => {
            const meta = TYPE_META[item.alert_type] ?? {
              tone: "bg-muted-foreground/40",
              code: "—",
            };
            const pct = total ? (item.count / total) * 100 : 0;
            const barPct = (item.count / max) * 100;
            return (
              <li key={item.alert_type} className="space-y-2">
                <div className="flex items-baseline justify-between">
                  <div className="flex items-baseline gap-3">
                    <span className="font-mono text-[0.6rem] tracking-[0.22em] text-muted-foreground">
                      {meta.code}
                    </span>
                    <span className="text-sm text-foreground">
                      {formatAlertType(item.alert_type)}
                    </span>
                  </div>
                  <div className="font-mono tabular text-sm text-foreground">
                    {item.count}
                    <span className="ml-2 text-xs text-muted-foreground">
                      {pct.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="relative h-2 overflow-hidden bg-muted">
                  <div
                    className={cn(
                      "h-full transition-[width] duration-700 ease-out",
                      meta.tone
                    )}
                    style={{ width: `${barPct}%` }}
                  />
                  <div
                    className="pointer-events-none absolute inset-y-0 w-px bg-border"
                    style={{ left: "25%" }}
                  />
                  <div
                    className="pointer-events-none absolute inset-y-0 w-px bg-border"
                    style={{ left: "50%" }}
                  />
                  <div
                    className="pointer-events-none absolute inset-y-0 w-px bg-border"
                    style={{ left: "75%" }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
