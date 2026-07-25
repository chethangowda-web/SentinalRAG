"use client";

import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export interface PipelineStep {
  key: string;
  label: string;
  description: string;
  icon: LucideIcon;
}

export function PipelineStepTrail({
  steps,
  currentStep,
  isDone = false,
  isError = false,
  className,
}: {
  steps: readonly PipelineStep[];
  currentStep: string | null;
  isDone?: boolean;
  isError?: boolean;
  className?: string;
}) {
  const currentIdx = steps.findIndex((s) => s.key === currentStep);
  const stepIndex = currentIdx >= 0 ? currentIdx : -1;

  return (
    <div className={cn("space-y-1.5", className)}>
      {steps.map((step, i) => {
        const isStepDone = isDone || (!isError && stepIndex >= 0 && i < stepIndex);
        const isStepActive = !isDone && !isError && stepIndex >= 0 && i === stepIndex;
        const isStepWaiting = !isDone && !isError && (stepIndex < 0 || i > stepIndex);

        if (isStepWaiting) {
          return (
            <div
              key={step.key}
              className="flex items-center gap-3 rounded-lg px-4 py-2.5 opacity-35"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                <step.icon className="h-3.5 w-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-muted-foreground">{step.label}</p>
                <p className="text-[10px] text-muted-foreground/60">{step.description}</p>
              </div>
            </div>
          );
        }

        return (
          <motion.div
            key={step.key}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08 }}
            className={cn(
              "relative flex items-center gap-3 rounded-lg border px-4 py-2.5 transition-all duration-300",
              isStepActive && "border-confidence-high/30 bg-confidence-high-bg shadow-sm",
              isStepDone && "border-border/40 bg-muted/20",
            )}
          >
            <div
              className={cn(
                "relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-all",
                isStepDone && "bg-confidence-high text-white",
                isStepActive && "bg-confidence-high text-white",
                !isStepDone && !isStepActive && "bg-muted text-muted-foreground",
              )}
            >
              {isStepDone ? (
                <Check className="h-3.5 w-3.5" />
              ) : isStepActive ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <step.icon className="h-3.5 w-3.5" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p
                className={cn(
                  "text-xs font-medium transition-colors",
                  isStepDone && "text-confidence-high",
                  isStepActive && "text-foreground",
                  !isStepDone && !isStepActive && "text-muted-foreground",
                )}
              >
                {step.label}
              </p>
              <p className="text-[10px] text-muted-foreground/60">{step.description}</p>
            </div>
            {isStepActive && (
              <div className="flex gap-1 pr-1">
                <motion.span
                  className="h-1.5 w-1.5 rounded-full bg-confidence-high"
                  animate={{ scale: [1, 1.4, 1] }}
                  transition={{ duration: 1, repeat: Infinity, delay: 0 }}
                />
                <motion.span
                  className="h-1.5 w-1.5 rounded-full bg-confidence-high"
                  animate={{ scale: [1, 1.4, 1] }}
                  transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
                />
                <motion.span
                  className="h-1.5 w-1.5 rounded-full bg-confidence-high"
                  animate={{ scale: [1, 1.4, 1] }}
                  transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
                />
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
