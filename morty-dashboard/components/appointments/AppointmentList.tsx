"use client";

import { CalendarDays } from "lucide-react";
import AppointmentCard from "./AppointmentCard";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import type { Appointment } from "@/lib/types";

interface AppointmentListProps {
  appointments: Appointment[] | undefined;
  isLoading: boolean;
  onEdit?: (a: Appointment) => void;
  onCancel?: (a: Appointment) => void;
  onRemind?: (a: Appointment) => void;
  remindingId?: number | null;
  emptyTitle?: string;
  emptyDescription?: string;
}

export default function AppointmentList({
  appointments,
  isLoading,
  onEdit,
  onCancel,
  onRemind,
  remindingId,
  emptyTitle = "No appointments",
  emptyDescription = "Nothing scheduled here.",
}: AppointmentListProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner className="w-5 h-5" />
      </div>
    );
  }

  if (!appointments || appointments.length === 0) {
    return (
      <EmptyState
        icon={CalendarDays}
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }

  return (
    <div className="space-y-2">
      {appointments.map((a) => (
        <AppointmentCard
          key={a.id}
          appointment={a}
          onEdit={onEdit}
          onCancel={onCancel}
          onRemind={onRemind}
          remindPending={remindingId === a.id}
        />
      ))}
    </div>
  );
}
