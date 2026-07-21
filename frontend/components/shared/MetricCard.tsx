"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: { value: number; positive: boolean };
  color?: string;
  className?: string;
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color,
  className,
}: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "group relative overflow-hidden rounded-xl border bg-card p-6 transition-all duration-200 hover:shadow-md",
        className
      )}
    >
      {color && (
        <div
          className="absolute inset-0 opacity-[0.03] transition-opacity group-hover:opacity-[0.06]"
          style={{
            background: `linear-gradient(135deg, ${color} 0%, transparent 100%)`,
          }}
        />
      )}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold tracking-tight">{value}</p>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg",
              color ? "bg-background" : "bg-primary/10"
            )}
          >
            <Icon
              className="h-5 w-5"
              style={color ? { color } : undefined}
            />
          </div>
        )}
      </div>
      {trend && (
        <div className="mt-4 flex items-center gap-1.5">
          <span
            className={cn(
              "text-xs font-medium",
              trend.positive ? "text-success" : "text-destructive"
            )}
          >
            {trend.positive ? "+" : ""}
            {trend.value}%
          </span>
          <span className="text-xs text-muted-foreground">vs last period</span>
        </div>
      )}
    </motion.div>
  );
}
