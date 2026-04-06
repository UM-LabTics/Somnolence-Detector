import type {
  AlertNotificationResponse,
  DashboardSummary,
  DeviceResponse,
  HistoryResponse,
  TimelineEvent,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

function buildParams(
  params: Record<string, string | undefined>
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, value);
    }
  }
  const str = search.toString();
  return str ? `?${str}` : "";
}

export async function getDashboardSummary(
  deviceId?: string
): Promise<DashboardSummary> {
  const params = buildParams({ device_id: deviceId });
  return fetchApi<DashboardSummary>(`/api/dashboard/summary${params}`);
}

export async function getTimeline(
  deviceId?: string
): Promise<TimelineEvent[]> {
  const params = buildParams({ device_id: deviceId });
  return fetchApi<TimelineEvent[]>(`/api/dashboard/timeline${params}`);
}

export async function getHistory(params: {
  start_date: string;
  end_date: string;
  group_by: string;
  device_id?: string;
}): Promise<HistoryResponse> {
  const query = buildParams({
    start_date: `${params.start_date}T00:00:00`,
    end_date: `${params.end_date}T23:59:59`,
    group_by: params.group_by,
    device_id: params.device_id,
  });
  return fetchApi<HistoryResponse>(`/api/dashboard/history${query}`);
}

export async function getDevices(): Promise<DeviceResponse[]> {
  return fetchApi<DeviceResponse[]>("/api/devices/");
}

export async function getNotifications(params?: {
  device_id?: string;
  acknowledged?: boolean;
}): Promise<AlertNotificationResponse[]> {
  const query = buildParams({
    device_id: params?.device_id,
    acknowledged: params?.acknowledged?.toString(),
  });
  return fetchApi<AlertNotificationResponse[]>(
    `/api/notifications/${query}`
  );
}

export async function acknowledgeNotification(
  id: string
): Promise<AlertNotificationResponse> {
  return fetchApi<AlertNotificationResponse>(
    `/api/notifications/${id}/acknowledge`,
    { method: "PATCH" }
  );
}
