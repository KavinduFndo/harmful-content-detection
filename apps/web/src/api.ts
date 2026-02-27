import type { AlertDetail, AlertSummary, DebugModelCheckRequest, User } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Derive WebSocket base from API base (https -> wss, http -> ws) so only VITE_API_BASE_URL is needed. */
export const WS_BASE =
  import.meta.env.VITE_WS_BASE_URL ??
  (API_BASE.replace(/^https?:/, (m) => (m === "https:" ? "wss:" : "ws:")).replace(/\/$/, ""));

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

function jsonAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = localStorage.getItem("token");
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  return data.access_token as string;
}

export async function me(): Promise<User> {
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Unauthorized");
  return (await res.json()) as User;
}

export async function fetchAlerts(status?: "new" | "investigating" | "resolved"): Promise<AlertSummary[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const res = await fetch(`${API_BASE}/alerts${query}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load alerts");
  return (await res.json()) as AlertSummary[];
}

export async function fetchAlert(id: number): Promise<AlertDetail> {
  const res = await fetch(`${API_BASE}/alerts/${id}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load alert");
  return (await res.json()) as AlertDetail;
}

export async function patchAlert(id: number, payload: { status?: string; assigned_to?: number }) {
  const res = await fetch(`${API_BASE}/alerts/${id}`, {
    method: "PATCH",
    headers: jsonAuthHeaders(),
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("Failed to update alert");
  return res.json();
}

export async function sendFeedback(
  id: number,
  payload: { decision: "approve" | "reject"; corrected_category?: string; notes?: string }
) {
  const res = await fetch(`${API_BASE}/alerts/${id}/feedback`, {
    method: "POST",
    headers: jsonAuthHeaders(),
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("Failed to submit feedback");
  return res.json();
}

export async function listUsers(): Promise<User[]> {
  const res = await fetch(`${API_BASE}/users`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Failed to load users");
  return (await res.json()) as User[];
}

export async function debugModelCheck(payload: DebugModelCheckRequest): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/debug/model-check`, {
    method: "POST",
    headers: jsonAuthHeaders(),
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Debug model check failed: ${msg}`);
  }
  return (await res.json()) as Record<string, unknown>;
}
