import { api } from "./api";
import type { DashboardStats } from "@/types";

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/api/v1/dashboard/stats");
  return data;
}

export async function getDailyStats(): Promise<{ date: string; documents: number }[]> {
  const { data } = await api.get<{ date: string; documents: number }[]>("/api/v1/dashboard/daily-stats");
  return data;
}
