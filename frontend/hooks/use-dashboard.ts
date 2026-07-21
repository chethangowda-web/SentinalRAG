"use client";

import { useQuery } from "@tanstack/react-query";
import { getDashboardStats, getDailyStats } from "@/services/dashboard";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getDashboardStats,
    refetchInterval: 30000,
  });
}

export function useDailyStats() {
  return useQuery({
    queryKey: ["daily-stats"],
    queryFn: getDailyStats,
    refetchInterval: 60000,
  });
}
