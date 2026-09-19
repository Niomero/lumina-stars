const TOKEN_KEY = "lumina_token";
const ADMIN_KEY = "lumina_admin";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  clearAdminUnlock();
}

export function getAdminUnlock() {
  return localStorage.getItem(ADMIN_KEY);
}
export function setAdminUnlock(token: string) {
  localStorage.setItem(ADMIN_KEY, token);
}
export function clearAdminUnlock() {
  localStorage.removeItem(ADMIN_KEY);
}

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export async function api<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const unlock = getAdminUnlock();
  const method = (init.method || "GET").toUpperCase();
  if (unlock && path.startsWith("/admin") && !(path === "/admin/unlock" && method === "POST")) {
    headers["X-Admin-Unlock"] = unlock;
  }
  const res = await fetch(`/api/v1${path}`, { ...init, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || body.success === false) {
    const code = body?.error?.code || "ERROR";
    if (code === "ADMIN_LOCKED") {
      clearAdminUnlock();
      window.dispatchEvent(new Event("lumina-admin-lock"));
    }
    throw new ApiError(code, body?.error?.message || "Ошибка запроса", res.status);
  }
  return body.data as T;
}
