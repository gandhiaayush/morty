"use client";

import { useQuery } from "@tanstack/react-query";
import { getAnalytics } from "@/lib/api";

export function useAnalytics(days: number = 30) {
  return useQuery({
    queryKey: ["analytics", days],
    queryFn: () => getAnalytics(days),
    staleTime: 5 * 60_000,
  });
}
