"use client";

import { use } from "react";
import { ArrowLeft, Phone, Clock, Calendar, Hash } from "lucide-react";
import Link from "next/link";
import { useAppointment } from "@/hooks/useAppointments";
import Badge from "@/components/ui/Badge";
import CancelButton from "@/components/appointments/CancelButton";
import Spinner from "@/components/ui/Spinner";
import { formatDatetime, formatPhone, formatCurrency } from "@/lib/utils";
import { useServices } from "@/hooks/useServices";
import { useRouter } from "next/navigation";

export default function AppointmentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { data: appt, isLoading, isError } = useAppointment(Number(id));
  const { data: services } = useServices();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner className="w-5 h-5" />
      </div>
    );
  }

  if (isError || !appt) {
    return (
      <div className="p-6">
        <p className="text-sm text-zinc-500">Appointment not found.</p>
        <Link href="/dashboard" className="text-xs text-violet-400 hover:underline mt-2 inline-block">
          ← Back to dashboard
        </Link>
      </div>
    );
  }

  const svc = services?.find((s) => s.name === appt.service);

  return (
    <div className="p-6 max-w-xl space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-2">
          <Hash className="w-3.5 h-3.5 text-zinc-600" />
          <span className="mono text-zinc-400 text-sm">{appt.id}</span>
        </div>
        <Badge status={appt.status} />
      </div>

      {/* Detail card */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-800">
          <h1 className="text-base font-semibold text-zinc-100">
            {appt.customer?.name || "Unknown Customer"}
          </h1>
          {appt.customer?.phone && (
            <div className="flex items-center gap-1.5 mt-1">
              <Phone className="w-3 h-3 text-zinc-600" />
              <span className="mono text-zinc-400 text-xs">{formatPhone(appt.customer.phone)}</span>
            </div>
          )}
        </div>

        <div className="divide-y divide-zinc-800">
          <Row icon={Calendar} label="Date & Time" value={formatDatetime(appt.datetime)} />
          <Row icon={Clock} label="Duration" value={`${appt.duration_min} minutes`} />
          <Row label="Service" value={appt.service} />
          {svc && <Row label="Price" value={formatCurrency(svc.price)} />}
          <Row label="Reminder" value={appt.reminder_sent ? "Sent" : "Not sent"} />
          {appt.customer?.notes && <Row label="Notes" value={appt.customer.notes} />}
        </div>
      </div>

      {/* Actions */}
      {appt.status !== "cancelled" && (
        <div className="flex gap-2">
          <CancelButton appointmentId={appt.id} onDone={() => router.push("/dashboard")} />
        </div>
      )}
    </div>
  );
}

function Row({
  icon: Icon,
  label,
  value,
}: {
  icon?: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 px-5 py-3">
      {Icon && <Icon className="w-3.5 h-3.5 text-zinc-600 shrink-0" />}
      {!Icon && <span className="w-3.5 h-3.5 shrink-0" />}
      <span className="text-xs text-zinc-500 w-24 shrink-0">{label}</span>
      <span className="text-sm text-zinc-200">{value}</span>
    </div>
  );
}
