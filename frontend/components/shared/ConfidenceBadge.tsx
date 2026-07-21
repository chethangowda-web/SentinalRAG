import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { ConfidenceLevel } from "@/types";

const levelConfig: Record<ConfidenceLevel, { variant: "success" | "warning" | "destructive"; label: string }> = {
  HIGH: { variant: "success", label: "High" },
  MEDIUM: { variant: "warning", label: "Medium" },
  LOW: { variant: "destructive", label: "Low" },
};

export function ConfidenceBadge({
  level,
  score,
  className,
}: {
  level: ConfidenceLevel;
  score?: number;
  className?: string;
}) {
  const config = levelConfig[level];
  return (
    <Badge variant={config.variant} className={cn("gap-1", className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full bg-current")} />
      {config.label}
      {score !== undefined && ` (${Math.round(score)})`}
    </Badge>
  );
}
