"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { BehaviourCheck, EvaluationResult, PerQuestionResult, PipelineResult } from "@/types";

/* ─── behaviour checks ──────────────────────────────── */

/** What each kind of question should produce, and how many each pipeline got right. These are not noisy. */
export function BehaviourChecks({ checks }: { checks: BehaviourCheck[] }) {
  const shown = checks.filter((c) => c.total > 0);
  if (shown.length === 0) return null;
  return (
    <section aria-labelledby="behaviour-heading" className="space-y-3">
      <div>
        <h2 id="behaviour-heading" className="text-base font-semibold">Does it behave correctly?</h2>
        <p className="text-sm text-muted-foreground">
          Each kind of question should produce a particular behaviour. Unlike the keyword scores below, these results are not noisy.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {shown.map((c) => {
          const diff = c.sentinel - c.baseline;
          return (
            <Card key={c.label}>
              <CardContent className="space-y-2 p-4">
                <p className="text-sm font-medium leading-snug">{c.label}</p>
                <p className="text-xs text-muted-foreground">{c.description}</p>
                <div className="flex items-end justify-between pt-1">
                  <div>
                    <p className="text-2xl font-bold tabular-nums">
                      {c.sentinel}<span className="text-base font-medium text-muted-foreground">/{c.total}</span>
                    </p>
                    <p className="text-[11px] text-muted-foreground">SentinelRAG</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold tabular-nums text-muted-foreground">
                      {c.baseline}<span className="font-normal">/{c.total}</span>
                    </p>
                    <p className="text-[11px] text-muted-foreground">Plain RAG</p>
                  </div>
                </div>
                <p
                  className={cn(
                    "text-xs font-medium",
                    diff > 0 && "text-success",
                    diff < 0 && "text-destructive",
                    diff === 0 && "text-muted-foreground"
                  )}
                >
                  {diff > 0 ? `${diff} more than plain RAG` : diff < 0 ? `${-diff} fewer than plain RAG` : "Same as plain RAG"}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

/* ─── keyword metrics ───────────────────────────────── */

const METRICS: { key: string; label: string; help: string; higherIsBetter: boolean; kind: "percent" | "ms" }[] = [
  { key: "avg_faithfulness", label: "Faithfulness", help: "Share of the answer's words found in the retrieved text", higherIsBetter: true, kind: "percent" },
  { key: "avg_hallucination", label: "Hallucination rate", help: "Share of the answer not supported by the retrieved text", higherIsBetter: false, kind: "percent" },
  { key: "avg_answer_relevancy", label: "Answer relevancy", help: "How closely the answer matches the question's wording", higherIsBetter: true, kind: "percent" },
  { key: "avg_context_precision", label: "Context precision", help: "Share of retrieved passages that were relevant", higherIsBetter: true, kind: "percent" },
  { key: "avg_context_recall", label: "Context recall", help: "Share of the needed facts that were retrieved", higherIsBetter: true, kind: "percent" },
  { key: "avg_correctness", label: "Correctness", help: "Word overlap with the expected answer", higherIsBetter: true, kind: "percent" },
  { key: "avg_unsupported_answer_rate", label: "Unsupported answers", help: "Answers with little backing in the retrieved text", higherIsBetter: false, kind: "percent" },
  { key: "latency", label: "Mean response time", help: "Average time per question", higherIsBetter: false, kind: "ms" },
];

function formatValue(v: number | undefined, kind: "percent" | "ms") {
  if (v == null) return "--";
  return kind === "percent" ? `${(v * 100).toFixed(1)}%` : `${(v / 1000).toFixed(1)}s`;
}

export function MetricsTable({ summary }: { summary: EvaluationResult["summary"] }) {
  const rows = METRICS.map((m) => {
    const b = summary.baseline?.[m.key]?.value;
    const s = summary.sentinel?.[m.key]?.value;
    if (b == null || s == null) return null;
    // Tiny gaps are noise for keyword-overlap scores: call them level rather than a win
    const level = Math.abs(s - b) < (m.kind === "percent" ? 0.02 : 250);
    const winner = level ? "level" : (s > b) === m.higherIsBetter ? "sentinel" : "baseline";
    return { ...m, b, s, winner };
  }).filter((r): r is NonNullable<typeof r> => r !== null);
  if (rows.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Answer quality scores</CardTitle>
        <p className="text-sm text-muted-foreground">
          Keyword-overlap estimates over the benchmark questions. Swings of a few points between runs are normal, so
          read small gaps as &quot;level&quot;, not as a win or a loss.
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Baseline compared with SentinelRAG on each score</caption>
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th scope="col" className="py-2 pr-4 font-medium">Score</th>
                <th scope="col" className="px-4 py-2 text-right font-medium">Plain RAG</th>
                <th scope="col" className="px-4 py-2 text-right font-medium">SentinelRAG</th>
                <th scope="col" className="py-2 pl-4 text-right font-medium">Better</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className="border-b last:border-0">
                  <th scope="row" className="py-2.5 pr-4 text-left font-normal">
                    <span className="font-medium">{r.label}</span>
                    <span className="block text-xs text-muted-foreground">{r.help}</span>
                  </th>
                  <td className="px-4 py-2.5 text-right tabular-nums">{formatValue(r.b, r.kind)}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{formatValue(r.s, r.kind)}</td>
                  <td className="py-2.5 pl-4 text-right text-xs">
                    <span
                      className={cn(
                        "inline-block rounded-full px-2 py-0.5 font-medium",
                        r.winner === "sentinel" && "bg-success/10 text-success",
                        r.winner === "baseline" && "bg-muted text-muted-foreground",
                        r.winner === "level" && "bg-muted text-muted-foreground"
                      )}
                    >
                      {r.winner === "sentinel" ? "SentinelRAG" : r.winner === "baseline" ? "Plain RAG" : "Level"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

/* ─── per question ──────────────────────────────────── */

const FALLBACK_MARKER = "Based on the retrieved documents (source:";
const isFallback = (r: PipelineResult) => (r.answer ?? "").startsWith(FALLBACK_MARKER);

/** Answers that were raw retrieved text because the AI service failed: they count against the pipeline that hit them. */
export function FallbackNotice({ questions }: { questions: PerQuestionResult[] }) {
  const baseline = questions.filter((q) => isFallback(q.baseline)).length;
  const sentinel = questions.filter((q) => isFallback(q.sentinel)).length;
  if (baseline + sentinel === 0) return null;
  return (
    <div role="note" className="rounded-lg border border-confidence-medium/40 bg-confidence-medium-bg px-4 py-3 text-sm text-confidence-medium">
      Some answers are raw retrieved text because the AI service was unavailable or rate limited
      ({sentinel} for SentinelRAG, {baseline} for plain RAG). They count against the pipeline that hit them, so run the
      evaluation again when the service is calm for a fairer result.
    </div>
  );
}

const CATEGORY_LABELS: Record<string, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
  contradictory: "Conflicting sources",
  missing_context: "Not in documents",
  ambiguous: "Vague",
};

function Flags({ r }: { r: PipelineResult }) {
  const flags: string[] = [];
  if (r.retry_count > 0) flags.push(`searched again ${r.retry_count}×`);
  if (r.contradiction_detected) flags.push("conflict flagged");
  if (r.clarification_needed) flags.push("asked to clarify");
  if (isFallback(r)) flags.push("raw text fallback");
  return flags.length ? (
    <p className="mt-1 text-[11px] text-muted-foreground">{flags.join(" · ")}</p>
  ) : null;
}

function AnswerBlock({ title, result }: { title: string; result: PipelineResult }) {
  const text = result.answer ?? (result.clarification_needed ? result.clarification_question : null);
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs font-medium text-muted-foreground">{title}</p>
      <p className="mt-1 whitespace-pre-wrap text-sm">{text ?? "No answer"}</p>
      <Flags r={result} />
    </div>
  );
}

export function PerQuestionList({ questions }: { questions: PerQuestionResult[] }) {
  const [open, setOpen] = useState<string | null>(null);
  if (questions.length === 0) return null;
  return (
    <section aria-labelledby="questions-heading" className="space-y-3">
      <div>
        <h2 id="questions-heading" className="text-base font-semibold">Every question and both answers</h2>
        <p className="text-sm text-muted-foreground">Open a question to compare the expected answer with what each pipeline said.</p>
      </div>
      <ul className="divide-y rounded-xl border bg-card">
        {questions.map((q) => {
          const expanded = open === q.id;
          return (
            <li key={q.id}>
              <button
                type="button"
                onClick={() => setOpen(expanded ? null : q.id)}
                aria-expanded={expanded}
                className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-secondary/40"
              >
                <span className="w-6 shrink-0 text-xs tabular-nums text-muted-foreground">{q.id}</span>
                <span className="min-w-0 flex-1 text-sm font-medium">{q.question}</span>
                <span className="hidden shrink-0 rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground sm:inline">
                  {CATEGORY_LABELS[q.category] ?? q.category}
                </span>
                <ChevronDown className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform", expanded && "rotate-180")} />
              </button>
              {expanded && (
                <div className="space-y-3 px-4 pb-4">
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-xs font-medium text-muted-foreground">Expected</p>
                    <p className="mt-1 text-sm">{q.ground_truth}</p>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <AnswerBlock title="Plain RAG" result={q.baseline} />
                    <AnswerBlock title="SentinelRAG" result={q.sentinel} />
                  </div>
                  {q.sentinel.reasoning_path?.length > 0 && (
                    <p className="text-[11px] text-muted-foreground">Path taken: {q.sentinel.reasoning_path.join(" → ")}</p>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
