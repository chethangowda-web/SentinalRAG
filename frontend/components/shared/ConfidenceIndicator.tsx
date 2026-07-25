"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { ConfidenceLevel } from "@/types";

interface ConfidenceIndicatorProps {
  level?: ConfidenceLevel;
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

const sizeMap = {
  sm: { gauge: 40, stroke: 4, fontSize: "text-[9px]", scoreSize: "text-[10px]" },
  md: { gauge: 56, stroke: 5, fontSize: "text-[10px]", scoreSize: "text-xs" },
  lg: { gauge: 80, stroke: 6, fontSize: "text-xs", scoreSize: "text-sm" },
};

const confidenceColor = (score: number) => {
  if (score >= 70) return "var(--confidence-high)";
  if (score >= 40) return "var(--confidence-medium)";
  return "var(--confidence-low)";
};

const levelLabel = (level?: ConfidenceLevel) => {
  if (level === "HIGH") return "High";
  if (level === "MEDIUM") return "Medium";
  if (level === "LOW") return "Low";
  return null;
};

export function ConfidenceIndicator({
  level,
  score,
  size = "md",
  showLabel = true,
  className,
}: ConfidenceIndicatorProps) {
  const dims = sizeMap[size];
  const radius = (dims.gauge - dims.stroke) / 2;
  const circumference = radius * 2 * Math.PI;
  const clamped = Math.min(Math.max(score, 0), 100);
  const offset = circumference - (clamped / 100) * circumference;
  const color = confidenceColor(clamped);
  const label = levelLabel(level);

  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      <div
        className="relative inline-flex items-center justify-center shrink-0"
        style={{ width: dims.gauge, height: dims.gauge }}
      >
        <svg width={dims.gauge} height={dims.gauge} className="-rotate-90">
          <circle
            cx={dims.gauge / 2}
            cy={dims.gauge / 2}
            r={radius}
            fill="none"
            stroke="hsl(var(--secondary))"
            strokeWidth={dims.stroke}
          />
          <motion.circle
            cx={dims.gauge / 2}
            cy={dims.gauge / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={dims.stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            key={clamped}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            className={cn("font-system-mono font-bold leading-none", dims.scoreSize)}
            style={{ color }}
          >
            {Math.round(clamped)}
          </motion.span>
          <span className={cn("leading-none text-muted-foreground", dims.fontSize)}>
            %
          </span>
        </div>
      </div>
      {showLabel && label && (
        <div className="flex flex-col leading-tight">
          <span className={cn("font-system-mono font-bold", dims.fontSize)} style={{ color }}>
            {label}
          </span>
          {level && (
            <span className="text-[9px] text-muted-foreground">
              Confidence
            </span>
          )}
        </div>
      )}
    </div>
  );
}
