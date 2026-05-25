import type {
  AlertNotificationResponse,
  AlertResponse,
  DashboardSummary,
  DeviceResponse,
  HistoryResponse,
  TimelineEvent,
  TokenResponse,
  UserCreatePayload,
  UserResponse,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_STORAGE_KEY = "somnolence_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  document.cookie = `${TOKEN_STORAGE_KEY}=${token}; path=/; max-age=${60 * 60 * 24}; SameSite=Lax`;
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  document.cookie = `${TOKEN_STORAGE_KEY}=; path=/; max-age=0; SameSite=Lax`;
}

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearStoredToken();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
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

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  return fetchApi<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe(): Promise<UserResponse> {
  return fetchApi<UserResponse>("/api/auth/me");
}

export async function listUsers(): Promise<UserResponse[]> {
  return fetchApi<UserResponse[]>("/api/auth/users");
}

export async function createUser(
  payload: UserCreatePayload
): Promise<UserResponse> {
  return fetchApi<UserResponse>("/api/auth/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
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

export async function getAlerts(params: {
  device_id?: string;
  alert_type?: string;
  severity?: string;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
}): Promise<AlertResponse[]> {
  const query = buildParams({
    device_id: params.device_id,
    alert_type: params.alert_type,
    severity: params.severity,
    start_date: params.start_date ? `${params.start_date}T00:00:00` : undefined,
    end_date: params.end_date ? `${params.end_date}T23:59:59` : undefined,
    skip: params.skip?.toString(),
    limit: params.limit?.toString(),
  });
  return fetchApi<AlertResponse[]>(`/api/alerts/${query}`);
}

export async function acknowledgeNotification(
  id: string
): Promise<AlertNotificationResponse> {
  return fetchApi<AlertNotificationResponse>(
    `/api/notifications/${id}/acknowledge`,
    { method: "PATCH" }
  );
}
