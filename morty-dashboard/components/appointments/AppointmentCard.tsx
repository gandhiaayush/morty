"use client";

import { Phone, Clock, Bell, BellOff, Edit2, Trash2 } from "lucide-react";
import Badge from "@/components/ui/Badge";
import { formatDatetime, formatPhone } from "@/lib/utils";
import type { Appointment } from "@/lib/types";

interface AppointmentCardProps {
  appointment: Appointment;
  onEdit?: (a: Appointment) => void;
  onCancel?: (a: Appointment) => void;
  onRemind?: (a: Appointment) => void;
  remindPending?: boolean;
}

export default function AppointmentCard({
  appointment: a,
  onEdit,
  onCancel,
  onRemind,
  remindPending,
}: AppointmentCardProps) {
  const isCancelled = a.status === "cancelled";

  return (
    <div
      className={`group bg-zinc-900 border rounded-lg px-4 py-3 flex items-start gap-4 transition-colors ${
        isCancelled ? "border-zinc-800 opacity-60" : "border-zinc-800 hover:border-zinc-700"
      }`}
    >
      {/* Left: time stripe */}
      <div className="flex flex-col items-center gap-0.5 min-w-[52px]">
        <span className="mono text-zinc-300 text-xs font-medium">
          {formatDatetime(a.datetime).split("·")[1]?.trim() ?? ""}
        </span>
        <span className="text-[10px] text-zinc-600">
          {a.duration_min}m
        </span>
      </div>

      {/* Center: details */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-zinc-100 truncate">
            {a.customer?.name || "Unknown"}
          </span>
          <Badge status={a.status} />
        </div>

        <div className="flex items-center gap-3 mt-1 flex-wrap">
          <span className="text-xs text-zinc-400">{a.service}</span>
          {a.customer?.phone && (
            <span className="mono text-zinc-500 flex items-center gap-1">
              <Phone className="w-2.5 h-2.5" />
              {formatPhone(a.customer.phone)}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 mt-1.5">
          <Clock className="w-3 h-3 text-zinc-600" />
          <span className="mono text-zinc-600 text-[11px]">{formatDatetime(a.datetime)}</span>
          <span className="mono text-zinc-700 text-[11px] ml-2">#{a.id}</span>
        </div>
      </div>

      {/* Right: actions */}
      {!isCancelled && (
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          {onRemind && (
            <button
              onClick={() => onRemind(a)}
              disabled={remindPending || a.reminder_sent}
              title={a.reminder_sent ? "Reminder already sent" : "Send reminder call"}
              className="p-1.5 rounded text-zinc-500 hover:text-amber-400 hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {a.reminder_sent ? (
                <BellOff className="w-3.5 h-3.5" />
              ) : (
                <Bell className="w-3.5 h-3.5" />
              )}
            </button>
          )}
          {onEdit && (
            <button
              onClick={() => onEdit(a)}
              title="Edit appointment"
              className="p-1.5 rounded text-zinc-500 hover:text-violet-400 hover:bg-zinc-800 transition-colors"
            >
              <Edit2 className="w-3.5 h-3.5" />
            </button>
          )}
          {onCancel && (
            <button
              onClick={() => onCancel(a)}
              title="Cancel appointment"
              className="p-1.5 rounded text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
