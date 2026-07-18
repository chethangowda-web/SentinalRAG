"use client";

import { cn } from "@/lib/utils";
import type { ConfidenceLevel } from "@/types";

interface ConfidenceBadgeProps {
  level: ConfidenceLevel;
  score?: number;
  className?: string;
}

const config: Record<ConfidenceLevel, { color: string; icon: string }> = {
  HIGH: { color: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30", icon: "●" },
  MEDIUM: { color: "bg-amber-500/10 text-amber-500 border-amber-500/30", icon: "●" },
  LOW: { color: "bg-red-500/10 text-red-500 border-red-500/30", icon: "●" },
};

export function ConfidenceBadge({ level, score, className }: ConfidenceBadgeProps) {
  const cfg = config[level];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium", cfg.color, className)}>
      <span>{cfg.icon}</span>
      {level}
      {score !== undefined && <span className="opacity-70">({score.toFixed(1)})</span>}
    </span>
  );
}
