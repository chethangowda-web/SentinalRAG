"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams } from "next/navigation";
import { useEvaluationReport, useEvaluationHistory, useRunEvaluation, useEvaluationLatest, useSetupBenchmark } from "@/hooks/use-evaluation";
import { getDocumentEvaluation } from "@/services/evaluation";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import toast from "react-hot-toast";
import {
  BarChart3,
  Play,
  History,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Shield,
  Gauge,
  RefreshCw,
  XCircle,
  Brain,
  Target,
  Activity,
  Download,
  FileText,
  Layers,
  Clock,
  Scan,
  BookOpen,
  Zap,
  Sparkles,
  Award,
  Percent,
  RotateCw,
  Eye,
  Database,
} from "lucide-react";
import { EvaluationWorkflow } from "@/components/evaluation/EvaluationWorkflow";
import { BehaviourChecks, FallbackNotice, MetricsTable, PerQuestionList } from "@/components/evaluation/ReportSections";

function CircularProgress({ value, size = 140, strokeWidth = 10 }: { value: number; size?: number; strokeWidth?: number }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;
  const color = value >= 70 ? "hsl(var(--confidence-high))" : value >= 40 ? "hsl(var(--confidence-medium))" : "hsl(var(--confidence-low))";

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="hsl(var(--secondary))" strokeWidth={strokeWidth} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold" style={{ color }}>{Math.round(value)}</span>
        <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Score</span>
      </div>
    </div>
  );
}

function MetricBar({ value, label, icon: Icon, color, suffix = "%" }: { value: number; label: string; icon: React.ElementType; color: string; suffix?: string }) {
  const pct = Math.min(value, 100);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <div className="flex h-6 w-6 items-center justify-center rounded-md" style={{ backgroundColor: `${color}15` }}>
            <Icon className="h-3.5 w-3.5" style={{ color }} />
          </div>
          <span className="text-xs text-muted-foreground">{label}</span>
        </div>
          <span className="text-xs font-semibold font-system-mono tabular-nums" style={{ color }}>{value.toFixed(1)}{suffix}</span>
      </div>
      <div className="h-2 rounded-full bg-secondary overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function KnowledgeCard({ label, value, icon: Icon, color, subtitle }: { label: string; value: string | number; icon: React.ElementType; color: string; subtitle?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="group relative overflow-hidden rounded-xl border bg-card p-4 transition-all duration-200 hover:shadow-md hover:border-primary/20"
    >
      <div className="absolute inset-0 opacity-[0.02] transition-opacity group-hover:opacity-[0.05]" style={{ background: `linear-gradient(135deg, ${color} 0%, transparent 100%)` }} />
      <div className="relative flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" style={{ backgroundColor: `${color}15` }}>
          <Icon className="h-5 w-5" style={{ color }} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-xl font-bold font-system-mono tracking-tight mt-0.5">{value}</p>
          {subtitle && <p className="text-[10px] text-muted-foreground mt-0.5">{subtitle}</p>}
        </div>
      </div>
    </motion.div>
  );
}

function StatusBadgePill({ status }: { status: string }) {
  const config: Record<string, { color: string; bg: string }> = {
    completed: { color: "text-success", bg: "bg-success/10" },
    running: { color: "text-primary", bg: "bg-primary/10" },
    failed: { color: "text-destructive", bg: "bg-destructive/10" },
    processing: { color: "text-warning", bg: "bg-warning/10" },
    pending: { color: "text-muted-foreground", bg: "bg-muted" },
  };
  const c = config[status] ?? config.pending;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${c.color} ${c.bg}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.color.replace("text-", "bg-").replace("/10", "")}`} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function exportEvalReport(report: any) {
  const text = [
    "# SentinelRAG Evaluation Report",
    `Timestamp: ${report.timestamp ?? new Date().toISOString()}`,
    `Total Questions: ${report.total_questions ?? "N/A"}`,
    "",
    "## Sentinel Metrics",
    ...Object.entries(report.summary?.sentinel ?? {}).map(([key, val]: [string, any]) =>
      `${key.replace(/_/g, " ")}: ${val.value != null ? `${(val.value * 100).toFixed(1)}%` : "N/A"}`
    ),
    "",
    "## Comparison vs Baseline",
    ...Object.entries(report.summary?.comparison ?? {}).map(([key, val]: [string, any]) => {
      const v = val as any;
      return `${key.replace(/_/g, " ")}: ${v.baseline != null ? `${(v.baseline * 100).toFixed(1)}%` : "N/A"} → ${v.sentinel != null ? `${(v.sentinel * 100).toFixed(1)}%` : "N/A"} (${v.improved ? "improved" : "regressed"})`;
    }),
  ].join("\n");

  const blob = new Blob([text], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `evaluation-report-${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function EvaluationPage() {
  const searchParams = useSearchParams();
  const docIdFromUrl = searchParams.get("document_id");

  const { data: report, isLoading: reportLoading } = useEvaluationReport();
  const { data: history, isLoading: historyLoading } = useEvaluationHistory();
  const runEval = useRunEvaluation();
  const latest = useEvaluationLatest();
  const setupBenchmark = useSetupBenchmark();
  const benchmark = latest.data?.benchmark;
  const benchmarkReady = !!benchmark?.ready;
  const benchmarkLoading = setupBenchmark.isPending || !!benchmark?.loading;

  const [docEval, setDocEval] = useState<any | null>(null);
  const [docEvalLoading, setDocEvalLoading] = useState(false);

  useEffect(() => {
    if (docIdFromUrl) {
      setDocEvalLoading(true);
      getDocumentEvaluation(docIdFromUrl)
        .then((data) => setDocEval(data))
        .catch(() => setDocEval(null))
        .finally(() => setDocEvalLoading(false));
    } else {
      setDocEval(null);
    }
  }, [docIdFromUrl]);

  const handleRun = async (full = false) => {
    try {
      if (!benchmarkReady) {
        await setupBenchmark.mutateAsync();
        toast.success("Loading the benchmark documents...");
        return;
      }
      await runEval.mutateAsync(full);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Evaluation failed to start");
    }
  };

  // The server remembers a run in flight, so it is still shown after a reload.
  const serverRun = latest.data?.run;
  const isRunning = runEval.evalStatus?.status === "running" || serverRun?.status === "running";
  const runProgress = runEval.evalStatus?.progress ?? serverRun?.progress ?? 0;
  const runTotal = runEval.evalStatus?.total ?? serverRun?.total ?? 9;
  const runSteps = runEval.evalStatus?.steps ?? serverRun?.steps;
  const runStage = runEval.evalStatus?.stage ?? serverRun?.stage;
  const runError = runEval.evalStatus?.error ?? (serverRun?.status === "failed" ? serverRun.error ?? "The last run did not finish" : null);

  const summary = report?.summary;
  const s = summary?.sentinel;




  const docEvalOverall = docEval?.overall_score != null ? docEval.overall_score * 100 : null;

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        {docIdFromUrl && (
          <div className="rounded-xl border bg-card p-6">
            {docEvalLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading document evaluation...
              </div>
            ) : docEval ? (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold">Document Evaluation</h2>
                    <p className="text-sm text-muted-foreground">Document {docIdFromUrl.slice(0, 8)}...</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <CircularProgress value={docEvalOverall ?? 0} size={80} strokeWidth={8} />
                  </div>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <MetricBar value={(docEval.faithfulness ?? 0) * 100} label="Faithfulness" icon={Shield} color="hsl(var(--chart-1))" />
                  <MetricBar value={(docEval.correctness ?? 0) * 100} label="Correctness" icon={CheckCircle2} color="hsl(var(--chart-2))" />
                  <MetricBar value={(docEval.hallucination_rate ?? 0) * 100} label="Hallucination" icon={AlertTriangle} color="hsl(var(--confidence-low))" />
                  <MetricBar value={(docEval.answer_relevancy ?? 0) * 100} label="Answer Relevancy" icon={Target} color="hsl(var(--chart-3))" />
                  <MetricBar value={(docEval.context_recall ?? 0) * 100} label="Context Recall" icon={BookOpen} color="hsl(var(--chart-4))" />
                  <MetricBar value={(docEval.precision ?? 0) * 100} label="Precision" icon={Gauge} color="hsl(var(--chart-1))" />
                  <MetricBar value={(docEval.retrieval_score ?? 0) * 100} label="Retrieval Score" icon={Database} color="hsl(var(--chart-2))" />
                  <MetricBar value={(docEval.ocr_confidence ?? 0) * 100} label="OCR Quality" icon={Scan} color="hsl(var(--chart-3))" />
                </div>
                <div className="mt-3 text-xs text-muted-foreground">
                  {docEval.total_questions} questions · {docEval.processing_time?.toFixed(1)}s processing time
                  {docEval.created_at && ` · ${new Date(docEval.created_at).toLocaleDateString()}`}
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">No evaluation found for this document.</div>
            )}
          </div>
        )}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Evaluation Report</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Puts a plain RAG baseline and the self-correcting pipeline through the same short set of questions over six sample policy documents, including questions that should be refused, clarified or flagged as conflicting.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {benchmarkReady && !isRunning && !benchmarkLoading && (
              <Button variant="outline" size="sm" onClick={() => handleRun(true)} disabled={runEval.isPending} title="Runs all 18 benchmark questions; takes a few minutes">
                Run all 18 questions
              </Button>
            )}
            {runError && (
              <span className="text-sm text-destructive">Failed: {runError}</span>
            )}
            {report && !isRunning && (
              <Button variant="outline" size="sm" onClick={() => exportEvalReport(report)}>
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            )}
            <Button onClick={() => handleRun()} disabled={runEval.isPending || isRunning || benchmarkLoading}>
              {isRunning || benchmarkLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              {isRunning ? "Running..." : benchmarkLoading ? "Loading documents..." : benchmarkReady ? "Run Evaluation" : "Load benchmark documents"}
            </Button>
          </div>
        </div>

        {reportLoading ? (
          <LoadingSkeleton type="card" count={4} />
        ) : isRunning ? (
          <EvaluationWorkflow steps={runSteps} stage={runStage} total={runTotal} done={runProgress} />
        ) : report && s ? (
          <>
            <p className="text-xs text-muted-foreground">
              Last run {report.timestamp ? new Date(report.timestamp).toLocaleString() : "recently"} · {report.total_questions} questions · six sample policy documents
            </p>
            <BehaviourChecks checks={report.behaviour ?? []} />
            <FallbackNotice questions={report.per_question ?? []} />
            <MetricsTable summary={report.summary} />
            <PerQuestionList questions={report.per_question ?? []} />

            {history && history.length > 1 && (
              <section aria-labelledby="history-heading" className="space-y-3">
                <h2 id="history-heading" className="text-base font-semibold">Earlier runs</h2>
                <ul className="space-y-2">
                  {history.map((item, i) => (
                    <li key={item.evaluation_id ?? i} className="flex items-center justify-between rounded-lg border p-3 text-sm">
                      <span>{item.timestamp ? new Date(item.timestamp).toLocaleString() : "Unknown date"}</span>
                      <span className="text-xs text-muted-foreground">{item.total_questions ?? "?"} questions</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        ) : (
          <EmptyState
            icon={BarChart3}
            title="No Evaluation Data"
            description={
              benchmarkReady
                ? "The benchmark documents are loaded. Run the evaluation to compare the baseline with the self-correcting pipeline."
                : "The benchmark questions are about six sample policy documents, so they are added to your account first (a few seconds). You can delete them afterwards."
            }
            action={
              <div className="flex flex-col items-center gap-3">
                <Button onClick={() => handleRun()} disabled={runEval.isPending || benchmarkLoading} size="lg" className="gap-2">
                  {runEval.isPending || benchmarkLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  {benchmarkReady ? "Run Evaluation" : benchmarkLoading ? "Loading documents..." : "Load benchmark documents"}
                </Button>
                {benchmarkLoading && benchmark && (
                  <ul className="text-xs text-muted-foreground" aria-live="polite">
                    {benchmark.documents.map((d) => (
                      <li key={d.filename}>{d.filename}: {d.status === "embedded" ? "ready" : d.status === "missing" ? "waiting" : "indexing"}</li>
                    ))}
                  </ul>
                )}
              </div>
            }
          />
        )}
      </div>
    </ErrorBoundary>
  );
}
