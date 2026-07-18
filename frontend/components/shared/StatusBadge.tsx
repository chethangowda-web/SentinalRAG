"use client";

import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const statusConfig: Record<string, { color: string; label: string }> = {
  completed: { color: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30", label: "Completed" },
  processing: { color: "bg-blue-500/10 text-blue-500 border-blue-500/30", label: "Processing" },
  pending: { color: "bg-yellow-500/10 text-yellow-500 border-yellow-500/30", label: "Pending" },
  failed: { color: "bg-red-500/10 text-red-500 border-red-500/30", label: "Failed" },
  embedded: { color: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30", label: "Embedded" },
  uploaded: { color: "bg-blue-500/10 text-blue-500 border-blue-500/30", label: "Uploaded" },
  healthy: { color: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30", label: "Healthy" },
  error: { color: "bg-red-500/10 text-red-500 border-red-500/30", label: "Error" },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusConfig[status.toLowerCase()] || {
    color: "bg-secondary text-muted-foreground border-border",
    label: status,
  };

  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium", config.color, className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", status === "healthy" || status === "completed" || status === "embedded" ? "bg-emerald-500" : status === "processing" || status === "pending" || status === "uploaded" ? "bg-yellow-500" : "bg-red-500")} />
      {config.label}
    </span>
  );
}
