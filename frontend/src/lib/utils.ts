import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const ALERT_TYPE_LABELS: Record<string, string> = {
  EYE_CLOSURE: "Cierre de ojos",
  YAWN: "Bostezo",
  HEAD_NOD: "Cabeceo",
  PHONE_USE: "Uso de celular",
  PHONE_OBJECT: "Celular detectado",
};

export function formatAlertType(type: string): string {
  return ALERT_TYPE_LABELS[type] || type;
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("es-UY", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("es-UY", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "ahora";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days} dias`;
}

export function formatPeriod(iso: string, groupBy: string): string {
  const d = new Date(iso);
  if (groupBy === "hour") {
    return d.toLocaleTimeString("es-UY", { hour: "2-digit", minute: "2-digit", hour12: false });
  }
  if (groupBy === "day") {
    return d.toLocaleDateString("es-UY", { day: "2-digit", month: "2-digit" });
  }
  return d.toLocaleDateString("es-UY", { month: "2-digit", year: "numeric" });
}
