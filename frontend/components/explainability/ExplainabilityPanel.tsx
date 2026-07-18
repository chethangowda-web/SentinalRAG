"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, Shield, AlertTriangle, CheckCircle, RefreshCw, GitBranch } from "lucide-react";
import type { ChatResponse } from "@/types";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { LatencyBadge } from "@/components/shared/LatencyBadge";
import { ReasoningTimeline } from "@/components/shared/ReasoningTimeline";
import { CitationCard } from "@/components/shared/CitationCard";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface ExplainabilityPanelProps {
  response: ChatResponse | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ExplainabilityPanel({ response, isOpen, onClose }: ExplainabilityPanelProps) {
  if (!response) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 420, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
          className="relative border-l border-border bg-card overflow-hidden"
        >
          <div className="flex h-16 items-center justify-between border-b border-border px-4">
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">Explainability</h3>
            </div>
            <button onClick={onClose} className="rounded-lg p-1.5 text-muted-foreground hover:bg-secondary transition-colors">
              <X className="h-4 w-4" />
            </button>
          </div>

          <ScrollArea className="h-[calc(100vh-8rem)]">
            <div className="space-y-5 p-4">

              {/* Confidence */}
              <section>
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Confidence Score</p>
                <div className="flex items-center gap-3">
                  <ConfidenceBadge level={response.confidence_level} score={response.confidence} />
                  <LatencyBadge ms={Object.values(response.latencies || {}).reduce((a, b) => a + b, 0)} />
                </div>
              </section>

              <Separator />

              {/* Latency Breakdown */}
              {response.latencies && (
                <section>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Latency Breakdown</p>
                  <div className="space-y-1.5">
                    {Object.entries(response.latencies).map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">{key.replace(/_/g, " ")}</span>
                        <LatencyBadge ms={val} />
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <Separator />

              {/* Reasoning Path */}
              {response.reasoning_path && response.reasoning_path.length > 0 && (
                <section>
                  <ReasoningTimeline path={response.reasoning_path} />
                </section>
              )}

              <Separator />

              {/* Clarification */}
              {response.clarification_question && (
                <section className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                  <div className="flex items-center gap-2 text-amber-500">
                    <AlertTriangle className="h-4 w-4" />
                    <span className="text-xs font-medium">Clarification Needed</span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{response.clarification_question}</p>
                </section>
              )}

              {/* Citations */}
              {response.citations && response.citations.length > 0 && (
                <section>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Citations ({response.citations.length})
                  </p>
                  <div className="space-y-2">
                    {response.citations.map((cit, i) => (
                      <CitationCard key={i} citation={cit} index={i} />
                    ))}
                  </div>
                </section>
              )}
            </div>
          </ScrollArea>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
