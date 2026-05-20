import { format, parseISO, isToday, isTomorrow } from "date-fns";

export function formatPhone(phone: string): string {
  const cleaned = phone.replace(/\D/g, "");
  if (cleaned.length === 10) {
    return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
  }
  if (cleaned.length === 11 && cleaned[0] === "1") {
    return `+1 (${cleaned.slice(1, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
  }
  return phone;
}

export function normalizePhone(phone: string): string {
  return phone.replace(/[\s\-\(\)]/g, "");
}

export function formatDatetime(iso: string): string {
  const d = parseISO(iso);
  const dayLabel = isToday(d) ? "Today" : isTomorrow(d) ? "Tomorrow" : format(d, "EEE MMM d");
  return `${dayLabel} · ${format(d, "h:mm a")}`;
}

export function formatDate(iso: string): string {
  return format(parseISO(iso), "MMM d, yyyy");
}

export function formatTime(iso: string): string {
  return format(parseISO(iso), "h:mm a");
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);
}

export function todayISO(): string {
  return format(new Date(), "yyyy-MM-dd");
}

export function statusColor(status: string): string {
  switch (status) {
    case "booked":    return "badge-green";
    case "modified":  return "badge-amber";
    case "cancelled": return "badge-red";
    case "completed": return "badge-gray";
    default:          return "badge-gray";
  }
}
