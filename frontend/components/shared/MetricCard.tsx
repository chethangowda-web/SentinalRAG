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
  color?: "primary" | "emerald" | "amber" | "red" | "blue" | "purple";
  className?: string;
}

const colorMap = {
  primary: "from-primary/20 to-primary/5 border-primary/30",
  emerald: "from-emerald-500/20 to-emerald-500/5 border-emerald-500/30",
  amber: "from-amber-500/20 to-amber-500/5 border-amber-500/30",
  red: "from-red-500/20 to-red-500/5 border-red-500/30",
  blue: "from-blue-500/20 to-blue-500/5 border-blue-500/30",
  purple: "from-purple-500/20 to-purple-500/5 border-purple-500/30",
};

export function MetricCard({ title, value, subtitle, icon: Icon, trend, color = "primary", className }: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "relative overflow-hidden rounded-xl border bg-gradient-to-br p-5 backdrop-blur-sm",
        colorMap[color],
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold tracking-tight">{value}</p>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        {Icon && (
          <div className="rounded-lg bg-background/50 p-2 backdrop-blur-sm">
            <Icon className="h-5 w-5 text-foreground/70" />
          </div>
        )}
      </div>
      {trend && (
        <div className={cn("mt-3 flex items-center gap-1 text-xs font-medium", trend.positive ? "text-emerald-500" : "text-red-500")}>
          <span>{trend.positive ? "↑" : "↓"}</span>
          <span>{Math.abs(trend.value)}%</span>
          <span className="text-muted-foreground">vs baseline</span>
        </div>
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-transparent via-transparent to-white/[0.02] pointer-events-none" />
    </motion.div>
  );
}
