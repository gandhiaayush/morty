"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { format } from "date-fns";
import Modal from "@/components/ui/Modal";
import Spinner from "@/components/ui/Spinner";
import { useModifyAppointment } from "@/hooks/useAppointments";
import { useAvailability } from "@/hooks/useAvailability";
import { useServices } from "@/hooks/useServices";
import { formatTime } from "@/lib/utils";
import type { Appointment } from "@/lib/types";

const schema = z.object({
  service: z.string().optional(),
  date: z.string().optional(),
  slot: z.string().optional(),
  duration_min: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

interface ModifyModalProps {
  appointment: Appointment | null;
  onClose: () => void;
}

export default function ModifyModal({ appointment, onClose }: ModifyModalProps) {
  const modify = useModifyAppointment();
  const { data: services } = useServices();

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const date = watch("date");
  const existingDate = appointment ? format(new Date(appointment.datetime), "yyyy-MM-dd") : "";

  useEffect(() => {
    if (appointment) {
      reset({
        service: appointment.service,
        date: existingDate,
        slot: appointment.datetime,
        duration_min: String(appointment.duration_min),
      });
    }
  }, [appointment, existingDate, reset]);

  const { data: availability, isFetching: loadingSlots } = useAvailability(
    date ?? existingDate,
    !!(date ?? existingDate)
  );

  useEffect(() => { setValue("slot", ""); }, [date, setValue]);

  const onSubmit = async (data: FormData) => {
    if (!appointment) return;
    const changes: Record<string, string | number> = {};
    if (data.service && data.service !== appointment.service) changes.service = data.service;
    if (data.slot && data.slot !== appointment.datetime) changes.datetime = data.slot;
    const dur = data.duration_min ? parseInt(data.duration_min, 10) : undefined;
    if (dur && dur !== appointment.duration_min) changes.duration_min = dur;

    if (Object.keys(changes).length === 0) { onClose(); return; }

    await modify.mutateAsync({ appointment_id: appointment.id, changes });
    onClose();
  };

  const todayStr = format(new Date(), "yyyy-MM-dd");

  return (
    <Modal
      open={!!appointment}
      onClose={onClose}
      title={`Modify Appointment #${appointment?.id}`}
      width="md"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Service */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1">Service</label>
          <select
            {...register("service")}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 focus:border-violet-500 focus:outline-none"
          >
            {services?.filter((s) => s.active).map((s) => (
              <option key={s.id} value={s.name}>
                {s.name} · {s.duration_min}min · ${s.price}
              </option>
            ))}
          </select>
        </div>

        {/* Duration */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1">Duration (min)</label>
          <input
            type="number"
            {...register("duration_min")}
            min={15}
            step={15}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 mono focus:border-violet-500 focus:outline-none"
          />
        </div>

        {/* Date */}
        <div>
          <label className="block text-xs font-medium text-zinc-400 mb-1">Date</label>
          <input
            type="date"
            {...register("date")}
            min={todayStr}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 mono focus:border-violet-500 focus:outline-none"
          />
        </div>

        {/* Slots */}
        {(date ?? existingDate) && (
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">
              Time Slot {loadingSlots && <Spinner className="inline w-3 h-3 ml-1" />}
            </label>
            <div className="grid grid-cols-4 gap-1.5">
              {availability?.open_slots.map((slot) => (
                <label key={slot} className="cursor-pointer">
                  <input type="radio" {...register("slot")} value={slot} className="sr-only peer" />
                  <span className="block text-center mono text-xs py-1.5 rounded border border-zinc-700 peer-checked:border-violet-500 peer-checked:bg-violet-600/20 peer-checked:text-violet-300 text-zinc-400 hover:border-zinc-600 transition-colors">
                    {formatTime(slot)}
                  </span>
                </label>
              ))}
              {!loadingSlots && availability?.open_slots.length === 0 && (
                <p className="col-span-4 text-xs text-zinc-500">No open slots.</p>
              )}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={modify.isPending}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-semibold rounded-md transition-colors"
          >
            {modify.isPending && <Spinner className="w-3 h-3" />}
            Save Changes
          </button>
        </div>
      </form>
    </Modal>
  );
}
