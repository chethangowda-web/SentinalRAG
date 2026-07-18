"use client";

import { cn } from "@/lib/utils";
import { Clock } from "lucide-react";

interface LatencyBadgeProps {
  ms: number;
  className?: string;
}

export function LatencyBadge({ ms, className }: LatencyBadgeProps) {
  const color = ms < 500 ? "text-emerald-500" : ms < 1000 ? "text-amber-500" : "text-red-500";
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs font-medium", color, className)}>
      <Clock className="h-3 w-3" />
      {ms.toFixed(0)}ms
    </span>
  );
}
