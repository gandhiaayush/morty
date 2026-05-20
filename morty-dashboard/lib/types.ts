export type AppointmentStatus = "booked" | "modified" | "cancelled" | "completed";

export interface Customer {
  id: number;
  name: string;
  phone: string;
  notes?: string;
  created?: boolean;
}

export interface Service {
  id: number;
  name: string;
  duration_min: number;
  price: number;
  active: boolean;
}

export interface Appointment {
  id: number;
  customer_id: number;
  customer?: Customer;
  service: string;
  service_id?: number;
  datetime: string;
  duration_min: number;
  status: AppointmentStatus;
  reminder_sent: boolean;
}

export interface AvailabilityResult {
  date: string;
  open_slots: string[];
}

// ── Request payloads ──────────────────────────────────────────────────────────

export interface BookPayload {
  customer_phone: string;
  service: string;
  datetime: string;
  duration_min?: number;
}

export interface ModifyPayload {
  appointment_id: number;
  changes: {
    service?: string;
    datetime?: string;
    duration_min?: number;
  };
}

export interface CancelPayload {
  appointment_id: number;
}

export interface ServiceCreatePayload {
  name: string;
  duration_min: number;
  price: number;
}

export interface ServiceUpdatePayload {
  name?: string;
  duration_min?: number;
  price?: number;
  active?: boolean;
}

// ── Response shapes ───────────────────────────────────────────────────────────

export interface BookResult {
  appointment_id: number;
  status: string;
  datetime: string;
  service: string;
  customer: Customer;
}

export interface ModifyResult {
  appointment_id: number;
  status: string;
  updated_fields: string[];
}

export interface CancelResult {
  appointment_id: number;
  status: string;
}

export interface SearchResult {
  results: Appointment[];
}

export interface ReminderResult {
  appointment_id: number;
  status: string;
  message: string;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface DailyBooking {
  date: string;
  count: number;
  revenue: number;
}

export interface BusiestSlot {
  hour: number;
  count: number;
}

export interface AnalyticsData {
  total_booked: number;
  total_revenue: number;
  cancellation_rate: number;
  daily_bookings: DailyBooking[];
  busiest_slots: BusiestSlot[];
}
