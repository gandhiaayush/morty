"use client";

import { useState, useCallback } from "react";
import { Search } from "lucide-react";
import Header from "@/components/layout/Header";
import AppointmentList from "@/components/appointments/AppointmentList";
import BookingModal from "@/components/appointments/BookingModal";
import ModifyModal from "@/components/appointments/ModifyModal";
import { useSearchAppointments, useCancelAppointment, useSendReminder } from "@/hooks/useAppointments";
import type { Appointment } from "@/lib/types";

function useDebounce(delay = 300) {
  const [debounced, setDebounced] = useState("");
  const timerRef = { current: undefined as ReturnType<typeof setTimeout> | undefined };
  const update = useCallback(
    (v: string) => {
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setDebounced(v), delay);
    },
    [delay] // eslint-disable-line react-hooks/exhaustive-deps
  );
  return [debounced, update] as const;
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [debouncedQ, setDebounced] = useDebounce(300);
  const [bookingOpen, setBookingOpen] = useState(false);
  const [modifying, setModifying] = useState<Appointment | null>(null);
  const [remindingId, setRemindingId] = useState<number | null>(null);

  const { data: results, isLoading } = useSearchAppointments(debouncedQ);
  const cancel = useCancelAppointment();
  const remind = useSendReminder();

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    setDebounced(e.target.value);
  };

  const handleCancel = (a: Appointment) => {
    if (confirm(`Cancel appointment #${a.id}?`)) cancel.mutate({ appointment_id: a.id });
  };

  const handleRemind = (a: Appointment) => {
    setRemindingId(a.id);
    remind.mutate(a.id, { onSettled: () => setRemindingId(null) });
  };

  return (
    <>
      <Header
        title="Search"
        subtitle="Find appointments by name, phone, or ID"
        action={{ label: "New Appointment", onClick: () => setBookingOpen(true) }}
      />

      <div className="flex-1 p-6 space-y-5">
        {/* Search input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            value={query}
            onChange={handleSearch}
            placeholder="Search by name, phone, or appointment ID…"
            autoFocus
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg pl-9 pr-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-600 focus:border-violet-500 focus:outline-none"
          />
        </div>

        {/* Results */}
        <div>
          {debouncedQ && (
            <p className="text-xs text-zinc-500 mb-3">
              {results?.length ?? 0} result{results?.length !== 1 ? "s" : ""} for &quot;{debouncedQ}&quot;
            </p>
          )}
          <AppointmentList
            appointments={results}
            isLoading={isLoading && !!debouncedQ}
            onEdit={setModifying}
            onCancel={handleCancel}
            onRemind={handleRemind}
            remindingId={remindingId}
            emptyTitle={debouncedQ ? "No results found" : "Start typing to search"}
            emptyDescription={
              debouncedQ
                ? "Try a different name, phone number, or appointment ID."
                : "Search across all appointments instantly."
            }
          />
        </div>
      </div>

      <BookingModal open={bookingOpen} onClose={() => setBookingOpen(false)} />
      <ModifyModal appointment={modifying} onClose={() => setModifying(null)} />
    </>
  );
}
