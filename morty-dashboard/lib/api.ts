import type {
  BookPayload, BookResult,
  ModifyPayload, ModifyResult,
  CancelPayload, CancelResult,
  AvailabilityResult,
  SearchResult,
  Customer,
  Appointment,
  Service, ServiceCreatePayload, ServiceUpdatePayload,
  ReminderResult,
  AnalyticsData,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Appointments ──────────────────────────────────────────────────────────────

export function bookAppointment(payload: BookPayload): Promise<BookResult> {
  return request("/tools/book", { method: "POST", body: JSON.stringify(payload) });
}

export function modifyAppointment(payload: ModifyPayload): Promise<ModifyResult> {
  return request("/tools/modify", { method: "POST", body: JSON.stringify(payload) });
}

export function cancelAppointment(payload: CancelPayload): Promise<CancelResult> {
  return request("/tools/cancel", { method: "POST", body: JSON.stringify(payload) });
}

export function searchAppointments(q: string): Promise<SearchResult> {
  return request(`/tools/search?q=${encodeURIComponent(q)}`);
}

export function getTodayAppointments(): Promise<SearchResult> {
  return request("/tools/appointments/today");
}

export function getAppointment(id: number): Promise<Appointment> {
  return request(`/tools/appointments/${id}`);
}

export function getAvailability(date: string): Promise<AvailabilityResult> {
  return request(`/tools/availability?date=${encodeURIComponent(date)}`);
}

// ── Customers ─────────────────────────────────────────────────────────────────

export function getCustomer(phone: string): Promise<Customer> {
  return request(`/tools/customer?phone=${encodeURIComponent(phone)}`);
}

export function updateCustomer(
  id: number,
  payload: { name?: string; notes?: string }
): Promise<Customer> {
  return request(`/tools/customer/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

// ── Services ─────────────────────────────────────────────────────────────────

export function getServices(): Promise<Service[]> {
  return request("/tools/services");
}

export function createService(payload: ServiceCreatePayload): Promise<Service> {
  return request("/tools/services", { method: "POST", body: JSON.stringify(payload) });
}

export function updateService(id: number, payload: ServiceUpdatePayload): Promise<Service> {
  return request(`/tools/services/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteService(id: number): Promise<{ id: number; deleted: boolean }> {
  return request(`/tools/services/${id}`, { method: "DELETE" });
}

// ── Reminders ─────────────────────────────────────────────────────────────────

export function sendReminder(appointmentId: number): Promise<ReminderResult> {
  return request(`/tools/remind/${appointmentId}`, { method: "POST" });
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export function getAnalytics(days: number = 30): Promise<AnalyticsData> {
  return request(`/tools/analytics?days=${days}`);
}
