"use client";

import { useState } from "react";
import { CalendarDays, Users, BellRing, TrendingUp } from "lucide-react";
import Header from "@/components/layout/Header";
import AppointmentList from "@/components/appointments/AppointmentList";
import BookingModal from "@/components/appointments/BookingModal";
import ModifyModal from "@/components/appointments/ModifyModal";
import {
  useTodayAppointments,
  useCancelAppointment,
  useSendReminder,
} from "@/hooks/useAppointments";
import { formatCurrency } from "@/lib/utils";
import type { Appointment } from "@/lib/types";
import { useServices } from "@/hooks/useServices";

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color = "violet",
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  color?: "violet" | "emerald" | "amber" | "blue";
}) {
  const colors = {
    violet: "text-violet-400 bg-violet-600/10",
    emerald: "text-emerald-400 bg-emerald-600/10",
    amber: "text-amber-400 bg-amber-600/10",
    blue: "text-blue-400 bg-blue-600/10",
  };
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 flex items-center gap-3">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${colors[color]}`}>
        <Icon className={`w-4 h-4 ${colors[color].split(" ")[0]}`} />
      </div>
      <div>
        <p className="text-xs text-zinc-500">{label}</p>
        <p className="text-lg font-semibold text-zinc-100 leading-tight">{value}</p>
        {sub && <p className="text-[11px] text-zinc-600">{sub}</p>}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [bookingOpen, setBookingOpen] = useState(false);
  const [modifying, setModifying] = useState<Appointment | null>(null);
  const [remindingId, setRemindingId] = useState<number | null>(null);

  const { data: appointments, isLoading } = useTodayAppointments();
  const { data: services } = useServices();
  const cancel = useCancelAppointment();
  const remind = useSendReminder();

  const active = appointments?.filter((a) => a.status !== "cancelled") ?? [];
  const pendingReminders = active.filter((a) => !a.reminder_sent).length;
  const revenue = active.reduce((sum, a) => {
    const svc = services?.find((s) => s.name === a.service);
    return sum + (svc?.price ?? 0);
  }, 0);

  const handleRemind = (a: Appointment) => {
    setRemindingId(a.id);
    remind.mutate(a.id, { onSettled: () => setRemindingId(null) });
  };

  const handleCancel = (a: Appointment) => {
    if (confirm(`Cancel appointment #${a.id} for ${a.customer?.name ?? "this customer"}?`)) {
      cancel.mutate({ appointment_id: a.id });
    }
  };

  return (
    <>
      <Header
        title="Today"
        subtitle={`${active.length} appointment${active.length !== 1 ? "s" : ""} scheduled`}
        action={{ label: "New Appointment", onClick: () => setBookingOpen(true) }}
      />

      <div className="flex-1 p-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            icon={CalendarDays}
            label="Booked today"
            value={active.length}
            color="violet"
          />
          <StatCard
            icon={TrendingUp}
            label="Est. revenue"
            value={formatCurrency(revenue)}
            color="emerald"
          />
          <StatCard
            icon={BellRing}
            label="Need reminders"
            value={pendingReminders}
            sub="not yet called"
            color="amber"
          />
          <StatCard
            icon={Users}
            label="Unique customers"
            value={new Set(active.map((a) => a.customer_id)).size}
            color="blue"
          />
        </div>

        {/* Appointment list */}
        <div>
          <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">
            Schedule
          </h2>
          <AppointmentList
            appointments={appointments}
            isLoading={isLoading}
            onEdit={setModifying}
            onCancel={handleCancel}
            onRemind={handleRemind}
            remindingId={remindingId}
            emptyTitle="No appointments today"
            emptyDescription="Use the 'New Appointment' button to book one."
          />
        </div>
      </div>

      <BookingModal open={bookingOpen} onClose={() => setBookingOpen(false)} />
      <ModifyModal appointment={modifying} onClose={() => setModifying(null)} />
    </>
  );
}
