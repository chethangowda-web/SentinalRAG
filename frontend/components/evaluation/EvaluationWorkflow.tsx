"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Circle, FileCheck2, FileText, Gauge, HelpCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface WorkflowStep {
  id: string;
  question: string;
  category: string;
  state: "waiting" | "running" | "done" | "failed";
  baseline: "waiting" | "running" | "done" | "failed";
  sentinel: "waiting" | "running" | "done" | "failed";
}

type Stage = "questions" | "scoring" | "report";
type StageState = "waiting" | "running" | "done";

const CATEGORY_LABELS: Record<string, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
  contradictory: "Conflicting sources",
  missing_context: "Not in documents",
  ambiguous: "Vague",
};

function StateIcon({ state, className }: { state: StageState | WorkflowStep["state"]; className?: string }) {
  if (state === "done") return <CheckCircle2 className={cn("text-success", className)} aria-hidden="true" />;
  if (state === "running") return <Loader2 className={cn("animate-spin text-primary", className)} aria-hidden="true" />;
  if (state === "failed") return <AlertCircle className={cn("text-destructive", className)} aria-hidden="true" />;
  return <Circle className={cn("text-muted-foreground/50", className)} aria-hidden="true" />;
}

const STATE_WORDS: Record<string, string> = { waiting: "waiting", running: "working", done: "done", failed: "failed" };

function Lane({ name, state }: { name: string; state: WorkflowStep["state"] }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px]",
        state === "done" && "border-success/30 bg-success/10 text-success",
        state === "running" && "border-primary/30 bg-primary/10 text-primary",
        state === "failed" && "border-destructive/30 bg-destructive/10 text-destructive",
        state === "waiting" && "border-border text-muted-foreground"
      )}
    >
      <StateIcon state={state} className="h-3 w-3" />
      {name}
      <span className="sr-only">: {STATE_WORDS[state]}</span>
    </span>
  );
}

function Elapsed() {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);
  return <span className="tabular-nums">{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}</span>;
}

/** The evaluation as a live workflow: documents → questions (two pipelines each) → scoring → report. */
export function EvaluationWorkflow({
  steps,
  stage,
  total,
  done,
}: {
  steps: WorkflowStep[] | null | undefined;
  stage: string | null | undefined;
  total: number;
  done: number;
}) {
  const current: Stage = stage === "scoring" || stage === "report" ? stage : "questions";
  const order: Stage[] = ["questions", "scoring", "report"];
  const stateOf = (s: Stage): StageState => (order.indexOf(s) < order.indexOf(current) ? "done" : s === current ? "running" : "waiting");

  const nodes: { key: string; icon: React.ElementType; title: string; detail: string; state: StageState; body?: React.ReactNode }[] = [
    { key: "docs", icon: FileText, title: "Sample documents", detail: "Six policy documents are loaded and indexed", state: "done" },
    {
      key: "questions",
      icon: HelpCircle,
      title: "Ask the questions",
      detail: `${done} of ${total} answered by both pipelines`,
      state: stateOf("questions"),
      body: steps && steps.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {steps.map((s) => (
            <motion.li
              key={s.id}
              layout
              className={cn(
                "flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-lg border px-3 py-2",
                s.state === "running" ? "border-primary/30 bg-primary/5" : "bg-card"
              )}
            >
              <StateIcon state={s.state} className="h-4 w-4 shrink-0" />
              <span className={cn("min-w-0 flex-1 basis-48 truncate text-sm", s.state === "waiting" && "text-muted-foreground")} title={s.question}>{s.question}</span>
              <span className="hidden shrink-0 text-[11px] text-muted-foreground sm:inline">{CATEGORY_LABELS[s.category] ?? s.category}</span>
              <span className="flex shrink-0 gap-1.5">
                <Lane name="Plain RAG" state={s.baseline} />
                <Lane name="SentinelRAG" state={s.sentinel} />
              </span>
            </motion.li>
          ))}
        </ul>
      ),
    },
    { key: "scoring", icon: Gauge, title: "Score the answers", detail: "Compare every answer with the expected one", state: stateOf("scoring") },
    { key: "report", icon: FileCheck2, title: "Build the report", detail: "Behaviour checks, scores and every answer side by side", state: stateOf("report") },
  ];

  return (
    <div className="mx-auto w-full max-w-3xl" role="status" aria-live="polite">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold">Evaluation in progress</h2>
          <p className="text-sm text-muted-foreground">Usually about a minute. You can leave this page; the run keeps going.</p>
        </div>
        <p className="text-sm text-muted-foreground">Elapsed <Elapsed /></p>
      </div>
      <ol className="relative">
        {nodes.map((n, i) => (
          <li key={n.key} className="relative flex gap-4 pb-6 last:pb-0">
            {i < nodes.length - 1 && (
              <span
                aria-hidden="true"
                className={cn("absolute left-[19px] top-10 h-[calc(100%-2.5rem)] w-px", n.state === "done" ? "bg-success/50" : "bg-border")}
              />
            )}
            <span
              className={cn(
                "relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 bg-background",
                n.state === "done" && "border-success text-success",
                n.state === "running" && "border-primary text-primary",
                n.state === "waiting" && "border-border text-muted-foreground"
              )}
            >
              <n.icon className="h-4 w-4" aria-hidden="true" />
            </span>
            <div className="min-w-0 flex-1 pt-1.5">
              <div className="flex items-center gap-2">
                <p className={cn("text-sm font-semibold", n.state === "waiting" && "text-muted-foreground")}>{n.title}</p>
                <StateIcon state={n.state} className="h-3.5 w-3.5" />
                <span className="sr-only">{STATE_WORDS[n.state]}</span>
              </div>
              <p className="text-xs text-muted-foreground">{n.detail}</p>
              {n.body}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
