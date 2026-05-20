"use client";

import { useQuery } from "@tanstack/react-query";
import { getAvailability } from "@/lib/api";

export function useAvailability(date: string, enabled = true) {
  return useQuery({
    queryKey: ["availability", date],
    queryFn: () => getAvailability(date),
    enabled: enabled && !!date,
    staleTime: 60_000,
  });
}
