export type AlertType = "EYE_CLOSURE" | "YAWN" | "HEAD_NOD" | "PHONE_USE" | "PHONE_OBJECT";
export type Severity = "LOW" | "MEDIUM" | "HIGH";

export interface EnvironmentalAverages {
  avg_temperature: number | null;
  avg_humidity: number | null;
  avg_co2: number | null;
}

export interface AlertCountByType {
  alert_type: AlertType;
  count: number;
}

export interface RecentAlert {
  id: string;
  device_id: string;
  alert_type: AlertType;
  severity: Severity;
  value: number;
  threshold: number;
  timestamp: string;
}

export interface DashboardSummary {
  environmental: EnvironmentalAverages;
  alert_counts_by_type: AlertCountByType[];
  total_alerts: number;
  recent_alerts: RecentAlert[];
}

export interface TimelineEvent {
  timestamp: string;
  event_type: "alert" | "environmental";
  device_id: string;
  alert_type?: AlertType;
  severity?: Severity;
  value?: number;
  temperature?: number;
  humidity?: number;
  co2?: number;
}

export interface HistoryDataPoint {
  period: string;
  avg_temperature: number | null;
  avg_humidity: number | null;
  avg_co2: number | null;
  alert_count: number;
}

export interface HistoryResponse {
  group_by: string;
  start_date: string;
  end_date: string;
  data: HistoryDataPoint[];
}

export interface DeviceResponse {
  id: string;
  name: string;
  created_at: string;
  last_seen_at: string;
  is_active: boolean;
}

export interface AlertNotificationResponse {
  id: string;
  device_id: string;
  alert_count: number;
  time_window_minutes: number;
  alert_ids: string[];
  created_at: string;
  acknowledged: boolean;
}
