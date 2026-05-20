"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getServices, createService, updateService, deleteService } from "@/lib/api";
import type { ServiceCreatePayload, ServiceUpdatePayload } from "@/lib/types";

export const SERVICE_KEYS = {
  all: ["services"] as const,
  detail: (id: number) => ["services", id] as const,
};

export function useServices() {
  return useQuery({
    queryKey: SERVICE_KEYS.all,
    queryFn: getServices,
    staleTime: 5 * 60_000,
  });
}

export function useCreateService() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ServiceCreatePayload) => createService(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SERVICE_KEYS.all });
      toast.success("Service created.");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useUpdateService() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ServiceUpdatePayload }) =>
      updateService(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SERVICE_KEYS.all });
      toast.success("Service updated.");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useDeleteService() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteService(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: SERVICE_KEYS.all });
      toast.success("Service removed.");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}
