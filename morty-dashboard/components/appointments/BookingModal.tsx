"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { format } from "date-fns";
import Modal from "@/components/ui/Modal";
import Spinner from "@/components/ui/Spinner";
import { useBookAppointment } from "@/hooks/useAppointments";
import { useCustomerByPhone } from "@/hooks/useCustomers";
import { useAvailability } from "@/hooks/useAvailability";
import { useServices } from "@/hooks/useServices";
import { normalizePhone, formatTime } from "@/lib/utils";

const schema = z.object({
  phone: z.string().min(7, "Enter a valid phone number"),
  service: z.string().min(1, "Select a service"),
  date: z.string().min(1, "Select a date"),
  slot: z.string().min(1, "Select a time slot"),
});

type FormData = z.infer<typeof schema>;

interface BookingModalProps {
  open: boolean;
  onClose: () => void;
}

export default function BookingModal({ open, onClose }: BookingModalProps) {
  const book = useBookAppointment();
  const { data: services } = useServices();

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const phone = watch("phone");
  const date = watch("date");

  const normalizedPhone = normalizePhone(phone ?? "");
  const { data: customer, isFetching: lookingUpCustomer } = useCustomerByPhone(
    normalizedPhone,
    normalizedPhone.length >= 7
  );
  const { data: availability, isFetching: loadingSlots } = useAvailability(date, !!date);

  // Reset slot when date changes
  useEffect(() => { setValue("slot", ""); }, [date, setValue]);

  const onSubmit = async (data: FormData) => {
    const svc = services?.find((s) => s.name === data.service);
    await book.mutateAsync({
      customer_phone: normalizePhone(data.phone),
      service: data.service,
      datetime: data.slot,
      duration_min: svc?.duration_min,
    });
    reset();
    onClose();
  };

  const handleClose = () => { reset(); onClose(); };

  const todayStr = format(new Date(), "yyyy-MM-dd");

  return (
    <Modal open={open} onClose={handleClose} title="New Appointment" width="md">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Phone */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1">Customer Phone</label>
          <div className="relative">
            <input
              {...register("phone")}
              placeholder="+1 (555) 000-0000"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:border-violet-500 focus:outline-none mono"
            />
            {lookingUpCustomer && (
              <Spinner className="absolute right-3 top-2.5 w-4 h-4" />
            )}
          </div>
          {customer && !customer.created && (
            <p className="text-xs text-emerald-400 mt-1">
              Found: {customer.name || "Unnamed customer"} · #{customer.id}
            </p>
          )}
          {customer?.created && (
            <p className="text-xs text-amber-400 mt-1">New customer — will be created on book.</p>
          )}
          {errors.phone && <p className="text-xs text-red-400 mt-1">{errors.phone.message}</p>}
        </div>

        {/* Service */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1">Service</label>
          <select
            {...register("service")}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 focus:border-violet-500 focus:outline-none"
          >
            <option value="">Select a service…</option>
            {services?.filter((s) => s.active).map((s) => (
              <option key={s.id} value={s.name}>
                {s.name} · {s.duration_min}min · ${s.price}
              </option>
            ))}
          </select>
          {errors.service && <p className="text-xs text-red-400 mt-1">{errors.service.message}</p>}
        </div>

        {/* Date */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1">Date</label>
          <input
            type="date"
            {...register("date")}
            min={todayStr}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 focus:border-violet-500 focus:outline-none mono"
          />
          {errors.date && <p className="text-xs text-red-400 mt-1">{errors.date.message}</p>}
        </div>

        {/* Slots */}
        {date && (
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">
              Available Slots {loadingSlots && <Spinner className="inline w-3 h-3 ml-1" />}
            </label>
            {!loadingSlots && availability?.open_slots.length === 0 && (
              <p className="text-xs text-zinc-500">No open slots on this date.</p>
            )}
            <div className="grid grid-cols-4 gap-1.5">
              {availability?.open_slots.map((slot) => (
                <label key={slot} className="cursor-pointer">
                  <input type="radio" {...register("slot")} value={slot} className="sr-only peer" />
                  <span className="block text-center mono text-xs py-1.5 rounded border border-zinc-700 peer-checked:border-violet-500 peer-checked:bg-violet-600/20 peer-checked:text-violet-300 text-zinc-400 hover:border-zinc-600 hover:text-zinc-300 transition-colors">
                    {formatTime(slot)}
                  </span>
                </label>
              ))}
            </div>
            {errors.slot && <p className="text-xs text-red-400 mt-1">{errors.slot.message}</p>}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={handleClose}
            className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={book.isPending}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-semibold rounded-md transition-colors"
          >
            {book.isPending && <Spinner className="w-3 h-3" />}
            Book Appointment
          </button>
        </div>
      </form>
    </Modal>
  );
}
