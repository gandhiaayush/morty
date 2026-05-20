"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getCustomer, updateCustomer } from "@/lib/api";

export const CUSTOMER_KEYS = {
  all: ["customers"] as const,
  byPhone: (phone: string) => ["customers", "phone", phone] as const,
  byId: (id: number) => ["customers", id] as const,
};

export function useCustomerByPhone(phone: string, enabled = true) {
  return useQuery({
    queryKey: CUSTOMER_KEYS.byPhone(phone),
    queryFn: () => getCustomer(phone),
    enabled: enabled && phone.length >= 7,
    retry: false,
  });
}

export function useUpdateCustomer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { name?: string; notes?: string } }) =>
      updateCustomer(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: CUSTOMER_KEYS.all });
      toast.success("Customer updated.");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}
