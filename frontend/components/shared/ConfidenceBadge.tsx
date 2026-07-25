import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { ConfidenceLevel } from "@/types";

const levelConfig: Record<ConfidenceLevel, { className: string; label: string }> = {
  HIGH: {
    className: "border-confidence-high/30 bg-confidence-high-bg text-confidence-high hover:bg-confidence-high-bg",
    label: "High",
  },
  MEDIUM: {
    className: "border-confidence-medium/30 bg-confidence-medium-bg text-confidence-medium hover:bg-confidence-medium-bg",
    label: "Medium",
  },
  LOW: {
    className: "border-confidence-low/30 bg-confidence-low-bg text-confidence-low hover:bg-confidence-low-bg",
    label: "Low",
  },
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
    <Badge variant="outline" className={cn("gap-1 text-[10px] h-5 px-1.5 font-system-mono font-bold", config.className, className)}>
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          level === "HIGH" && "bg-confidence-high",
          level === "MEDIUM" && "bg-confidence-medium",
          level === "LOW" && "bg-confidence-low",
        )}
      />
      {config.label}
      {score !== undefined && ` ${Math.round(score)}%`}
    </Badge>
  );
}
