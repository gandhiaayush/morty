"use client";

import { useState } from "react";
import { Users, Phone, FileText, Edit2, Check, X } from "lucide-react";
import Header from "@/components/layout/Header";
import AppointmentList from "@/components/appointments/AppointmentList";
import ModifyModal from "@/components/appointments/ModifyModal";
import Spinner from "@/components/ui/Spinner";
import EmptyState from "@/components/ui/EmptyState";
import { useCustomerByPhone, useUpdateCustomer } from "@/hooks/useCustomers";
import { useSearchAppointments, useCancelAppointment, useSendReminder } from "@/hooks/useAppointments";
import { normalizePhone, formatPhone } from "@/lib/utils";
import type { Appointment } from "@/lib/types";

export default function CustomersPage() {
  const [rawPhone, setRawPhone] = useState("");
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [modifying, setModifying] = useState<Appointment | null>(null);
  const [remindingId, setRemindingId] = useState<number | null>(null);

  const phone = normalizePhone(rawPhone);
  const { data: customer, isFetching, isError } = useCustomerByPhone(phone, phone.length >= 7);
  const { data: apptResults, isLoading: loadingAppts } = useSearchAppointments(phone);
  const updateCustomer = useUpdateCustomer();
  const cancel = useCancelAppointment();
  const remind = useSendReminder();

  const appts = apptResults ?? [];

  const handleSaveName = () => {
    if (!customer || !nameInput.trim()) return;
    updateCustomer.mutate({ id: customer.id, payload: { name: nameInput.trim() } });
    setEditingName(false);
  };

  const handleRemind = (a: Appointment) => {
    setRemindingId(a.id);
    remind.mutate(a.id, { onSettled: () => setRemindingId(null) });
  };

  return (
    <>
      <Header title="Customers" subtitle="Look up customers by phone number" />

      <div className="flex-1 p-6 space-y-6">
        {/* Phone lookup */}
        <div className="relative max-w-xs">
          <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="tel"
            value={rawPhone}
            onChange={(e) => setRawPhone(e.target.value)}
            placeholder="+1 (555) 000-0000"
            autoFocus
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg pl-9 pr-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-600 mono focus:border-violet-500 focus:outline-none"
          />
          {isFetching && <Spinner className="absolute right-3 top-2.5 w-4 h-4" />}
        </div>

        {/* Customer card */}
        {customer && !isError && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 max-w-lg space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                {editingName ? (
                  <div className="flex items-center gap-2">
                    <input
                      autoFocus
                      value={nameInput}
                      onChange={(e) => setNameInput(e.target.value)}
                      className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm text-zinc-100 focus:border-violet-500 focus:outline-none"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleSaveName();
                        if (e.key === "Escape") setEditingName(false);
                      }}
                    />
                    <button onClick={handleSaveName} className="text-emerald-400 hover:text-emerald-300">
                      <Check className="w-4 h-4" />
                    </button>
                    <button onClick={() => setEditingName(false)} className="text-zinc-500 hover:text-zinc-300">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 group">
                    <h2 className="text-base font-semibold text-zinc-100">
                      {customer.name || <span className="text-zinc-500 italic">No name</span>}
                    </h2>
                    <button
                      onClick={() => { setNameInput(customer.name ?? ""); setEditingName(true); }}
                      className="text-zinc-600 hover:text-violet-400 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
                <p className="mono text-zinc-400 text-sm mt-0.5">{formatPhone(customer.phone)}</p>
              </div>
              <div className="text-right">
                <p className="mono text-xs text-zinc-600">ID</p>
                <p className="mono text-zinc-400 text-sm">#{customer.id}</p>
              </div>
            </div>

            {/* Notes */}
            <div className="flex items-start gap-2">
              <FileText className="w-3.5 h-3.5 text-zinc-600 mt-0.5 shrink-0" />
              <p className="text-xs text-zinc-500">{customer.notes || "No notes."}</p>
            </div>

            {/* Appointment stats */}
            <div className="flex gap-4 pt-2 border-t border-zinc-800">
              <div>
                <p className="text-xs text-zinc-600">Total visits</p>
                <p className="text-sm font-semibold text-zinc-200">{appts.filter((a: import("@/lib/types").Appointment) => a.status !== "cancelled").length}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-600">Cancelled</p>
                <p className="text-sm font-semibold text-zinc-200">{appts.filter((a: import("@/lib/types").Appointment) => a.status === "cancelled").length}</p>
              </div>
            </div>
          </div>
        )}

        {phone.length >= 7 && isError && (
          <p className="text-sm text-zinc-500">No customer found for this number.</p>
        )}

        {/* Appointment history */}
        {customer && (
          <div>
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">
              Appointment History
            </h3>
            <AppointmentList
              appointments={appts}
              isLoading={loadingAppts}
              onEdit={setModifying}
              onCancel={(a) => {
                if (confirm(`Cancel appointment #${a.id}?`)) cancel.mutate({ appointment_id: a.id });
              }}
              onRemind={handleRemind}
              remindingId={remindingId}
              emptyTitle="No appointments yet"
              emptyDescription="This customer has no appointment history."
            />
          </div>
        )}

        {!customer && phone.length < 7 && (
          <EmptyState
            icon={Users}
            title="Enter a phone number"
            description="Type a customer phone number above to look up their profile and appointment history."
          />
        )}
      </div>

      <ModifyModal appointment={modifying} onClose={() => setModifying(null)} />
    </>
  );
}
