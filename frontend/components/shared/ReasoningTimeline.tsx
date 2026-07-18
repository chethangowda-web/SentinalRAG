"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const nodeLabels: Record<string, string> = {
  retrieve: "Retrieve Chunks",
  confidence_evaluate: "Evaluate Confidence",
  rewrite_query: "Rewrite Query",
  retry_retrieve: "Retry Retrieval",
  contradiction_detect: "Detect Contradictions",
  clarification: "Request Clarification",
  generate_answer: "Generate Answer",
  fallback: "Fallback Response",
};

const nodeIcons: Record<string, string> = {
  retrieve: "🔍",
  confidence_evaluate: "📊",
  rewrite_query: "✏️",
  retry_retrieve: "🔄",
  contradiction_detect: "⚡",
  clarification: "❓",
  generate_answer: "🤖",
  fallback: "🛡️",
};

interface ReasoningTimelineProps {
  path: string[];
  className?: string;
}

export function ReasoningTimeline({ path, className }: ReasoningTimelineProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Reasoning Path</p>
      <div className="relative">
        <div className="absolute left-[11px] top-2 h-[calc(100%-16px)] w-[2px] bg-border" />
        <div className="space-y-3">
          {path.map((node, i) => (
            <motion.div
              key={node}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className="flex items-start gap-3"
            >
              <div className={cn(
                "relative z-10 flex h-6 w-6 items-center justify-center rounded-full border text-xs",
                i === path.length - 1
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-card text-muted-foreground"
              )}>
                {nodeIcons[node] || "●"}
              </div>
              <div className="flex-1 pt-0.5">
                <p className={cn(
                  "text-sm",
                  i === path.length - 1 ? "font-medium text-foreground" : "text-muted-foreground"
                )}>
                  {nodeLabels[node] || node}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
