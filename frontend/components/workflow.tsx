"use client";

import { motion } from "framer-motion";
import {
  Search,
  ShieldCheck,
  RefreshCw,
  AlertTriangle,
  HelpCircle,
  MessageSquare,
  FileX,
  CheckCircle2,
} from "lucide-react";

const steps = [
  { icon: Search, label: "Retrieve", description: "Hybrid search (Vector + BM25 + RRF + Cross-Encoder)" },
  { icon: ShieldCheck, label: "Evaluate", description: "Three-tier confidence check" },
  { icon: RefreshCw, label: "Rewrite", description: "LLM rewrites query for low confidence" },
  { icon: Search, label: "Retry", description: "Re-retrieve with improved query" },
  { icon: AlertTriangle, label: "Detect", description: "Check for contradictions" },
  { icon: HelpCircle, label: "Clarify", description: "Ask clarifying questions if ambiguous" },
  { icon: MessageSquare, label: "Generate", description: "Produce answer with citations" },
  { icon: CheckCircle2, label: "Fallback", description: "Graceful 'I don't know' when uncertain" },
];

export function Workflow() {
  return (
    <section id="workflow" className="border-t py-20 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Self-Correction Workflow
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            An 8-node LangGraph state machine that automatically detects and
            corrects low-confidence results.
          </p>
        </div>

        <div className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step, i) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              viewport={{ once: true }}
              className="relative rounded-xl border bg-card p-5"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <step.icon className="h-4 w-4" />
                </div>
                <span className="text-xs text-muted-foreground font-mono">
                  {String(i + 1).padStart(2, "0")}
                </span>
              </div>
              <h3 className="font-medium text-sm mb-1">{step.label}</h3>
              <p className="text-xs text-muted-foreground">{step.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
