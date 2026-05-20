"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  bookAppointment, modifyAppointment, cancelAppointment,
  searchAppointments, getTodayAppointments, getAppointment, sendReminder,
} from "@/lib/api";
import type { BookPayload, ModifyPayload, CancelPayload } from "@/lib/types";

export const APPT_KEYS = {
  all: ["appointments"] as const,
  today: ["appointments", "today"] as const,
  search: (q: string) => ["appointments", "search", q] as const,
  detail: (id: number) => ["appointments", id] as const,
};

export function useTodayAppointments() {
  return useQuery({
    queryKey: APPT_KEYS.today,
    queryFn: () => getTodayAppointments().then((r) => r.results),
    refetchInterval: 60_000,
  });
}

export function useSearchAppointments(q: string) {
  return useQuery({
    queryKey: APPT_KEYS.search(q),
    queryFn: () => searchAppointments(q).then((r) => r.results),
    enabled: true,
  });
}

export function useAppointment(id: number) {
  return useQuery({
    queryKey: APPT_KEYS.detail(id),
    queryFn: () => getAppointment(id),
  });
}

export function useBookAppointment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: BookPayload) => bookAppointment(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: APPT_KEYS.all });
      toast.success("Appointment booked!");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useModifyAppointment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ModifyPayload) => modifyAppointment(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: APPT_KEYS.all });
      toast.success("Appointment updated.");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useCancelAppointment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CancelPayload) => cancelAppointment(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: APPT_KEYS.all });
      toast.success("Appointment cancelled.");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useSendReminder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (appointmentId: number) => sendReminder(appointmentId),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: APPT_KEYS.detail(id) });
      qc.invalidateQueries({ queryKey: APPT_KEYS.today });
      toast.success("Reminder sent!");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}
