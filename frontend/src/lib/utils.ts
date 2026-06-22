import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Parse a UTC datetime string from the backend (no timezone suffix) as UTC. */
export function parseUtc(iso: string): Date {
  return new Date(/Z|[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + "Z");
}

const ALERT_TYPE_LABELS: Record<string, string> = {
  EYE_CLOSURE: "Cierre de ojos",
  YAWN: "Bostezo",
  HEAD_NOD: "Cabeceo",
  PHONE_USE: "Uso de celular",
};

export function formatAlertType(type: string): string {
  return ALERT_TYPE_LABELS[type] || type;
}

export function formatTime(iso: string): string {
  return parseUtc(iso).toLocaleTimeString("es-UY", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatDateTime(iso: string): string {
  return parseUtc(iso).toLocaleString("es-UY", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatRelativeTime(iso: string): string {
  const diff = Date.now() - parseUtc(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "ahora";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days} dias`;
}

export function formatPeriod(iso: string, groupBy: string): string {
  const d = parseUtc(iso);
  if (groupBy === "hour") {
    return d.toLocaleTimeString("es-UY", { hour: "2-digit", minute: "2-digit", hour12: false });
  }
  if (groupBy === "day") {
    return d.toLocaleDateString("es-UY", { day: "2-digit", month: "2-digit" });
  }
  return d.toLocaleDateString("es-UY", { month: "2-digit", year: "numeric" });
}
