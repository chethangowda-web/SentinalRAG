"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useEvaluationReport, useEvaluationHistory, useRunEvaluation } from "@/hooks/use-evaluation";
import { useDocuments } from "@/hooks/use-documents";
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
} from "lucide-react";

function CircularProgress({ value, size = 140, strokeWidth = 10 }: { value: number; size?: number; strokeWidth?: number }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;
  const color = value >= 80 ? "hsl(var(--success))" : value >= 50 ? "hsl(var(--warning))" : "hsl(var(--destructive))";

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
        <span className="text-xs font-semibold tabular-nums" style={{ color }}>{value.toFixed(1)}{suffix}</span>
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
          <p className="text-xl font-bold tracking-tight mt-0.5">{value}</p>
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
  const { data: report, isLoading: reportLoading } = useEvaluationReport();
  const { data: history, isLoading: historyLoading } = useEvaluationHistory();
  const { data: documents } = useDocuments();
  const runEval = useRunEvaluation();

  const handleRun = async () => {
    try {
      await runEval.mutateAsync();
    } catch { toast.error("Evaluation failed to start"); }
  };

  const isRunning = runEval.evalStatus?.status === "running";
  const runProgress = runEval.evalStatus?.progress ?? 0;
  const runTotal = runEval.evalStatus?.total ?? 18;
  const runError = runEval.evalStatus?.error;

  const summary = report?.summary;
  const s = summary?.sentinel;
  const c = summary?.comparison;

  const faithfulness = s?.avg_faithfulness?.value;
  const correctness = s?.avg_correctness?.value;
  const relevancy = s?.avg_answer_relevancy?.value;
  const recall = s?.avg_context_recall?.value;
  const precision = s?.avg_context_precision?.value;
  const retrySuccess = s?.retry_success_rate?.value;

  const allValues = [faithfulness, correctness, relevancy, recall, precision].filter((v): v is number => v != null);
  const overallScore = allValues.length > 0 ? (allValues.reduce((a, b) => a + b, 0) / allValues.length) * 100 : 0;
  const hallucinationRisk = faithfulness != null ? (1 - faithfulness) * 100 : null;
  const retrievalAccuracy = recall != null && precision != null ? ((recall + precision) / 2) * 100 : null;
  const avgConfidence = allValues.length > 0 ? (allValues.reduce((a, b) => a + b, 0) / allValues.length) * 100 : null;
  const selfCorrectionRate = retrySuccess != null ? (1 - retrySuccess) * 100 : null;

  const totalChunks = documents?.reduce((sum, d) => sum + (d.chunk_count || 0), 0) ?? null;
  const totalPages = documents?.reduce((sum, d) => sum + (d.pages || 0), 0) ?? null;
  const totalDocs = documents?.length ?? 0;

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Evaluation Report</h1>
            <p className="text-sm text-muted-foreground mt-1">
              AI document quality assessment and pipeline performance metrics.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {isRunning && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="tabular-nums">Evaluating {runProgress}/{runTotal}</span>
              </div>
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
            <Button onClick={handleRun} disabled={runEval.isPending || isRunning}>
              {isRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              {isRunning ? "Running..." : "Run Evaluation"}
            </Button>
          </div>
        </div>

        {reportLoading ? (
          <LoadingSkeleton type="card" count={4} />
        ) : isRunning ? (
          <div className="flex flex-col items-center py-16 text-center">
            <div className="relative mb-6">
              <Loader2 className="h-16 w-16 text-primary animate-spin" />
            </div>
            <h3 className="text-lg font-semibold">Evaluation in Progress</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-md">
              Testing your RAG pipeline against {runTotal} benchmark questions to measure accuracy, faithfulness, and retrieval quality.
            </p>
            <div className="w-full max-w-md mt-6 space-y-2">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Progress</span>
                <span className="tabular-nums">{runProgress}/{runTotal}</span>
              </div>
              <Progress value={(runProgress / Math.max(runTotal, 1)) * 100} className="h-2.5" />
            </div>
            <p className="text-xs text-muted-foreground mt-4">This typically takes 1-2 minutes</p>
          </div>
        ) : s ? (
          <>
            <div className="grid gap-6 lg:grid-cols-[auto_1fr]">
              <Card className="lg:w-[180px]">
                <CardContent className="flex flex-col items-center justify-center pt-6 pb-6">
                  <CircularProgress value={overallScore} size={150} strokeWidth={12} />
                  <p className="text-xs text-muted-foreground mt-3 font-medium">Overall Knowledge Score</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">{totalDocs} document{totalDocs !== 1 ? "s" : ""} analyzed</p>
                </CardContent>
              </Card>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <KnowledgeCard label="OCR Quality" value={faithfulness != null ? `${(faithfulness * 100).toFixed(0)}%` : "N/A"} icon={Scan} color="hsl(var(--chart-1))" subtitle="Text extraction quality" />
                <KnowledgeCard label="Retrieval Accuracy" value={retrievalAccuracy != null ? `${retrievalAccuracy.toFixed(1)}%` : "N/A"} icon={Target} color="hsl(var(--chart-2))" subtitle="Recall & precision avg" />
                <KnowledgeCard label="Chunk Coverage" value={recall != null ? `${(recall * 100).toFixed(0)}%` : "N/A"} icon={Layers} color="hsl(var(--chart-3))" subtitle="Context recall rate" />
                <KnowledgeCard label="Embedding Status" value={totalChunks != null ? `${totalChunks} chunks` : "N/A"} icon={Zap} color="hsl(var(--chart-4))" subtitle={totalDocs > 0 ? `${totalDocs} docs embedded` : "No documents"} />
                <KnowledgeCard label="Hallucination Risk" value={hallucinationRisk != null ? `${hallucinationRisk.toFixed(1)}%` : "N/A"} icon={AlertTriangle} color={hallucinationRisk != null && hallucinationRisk > 15 ? "hsl(var(--destructive))" : "hsl(var(--success))"} subtitle="Lower is better" />
                <KnowledgeCard label="Average Confidence" value={avgConfidence != null ? `${avgConfidence.toFixed(1)}%` : "N/A"} icon={Shield} color={avgConfidence != null && avgConfidence >= 70 ? "hsl(var(--success))" : "hsl(var(--warning))"} subtitle="Across all metrics" />
                <KnowledgeCard label="Self-Corrections" value={selfCorrectionRate != null ? `${selfCorrectionRate.toFixed(0)}%` : "N/A"} icon={RefreshCw} color="hsl(var(--chart-1))" subtitle="Query rewrite rate" />
                <KnowledgeCard label="Processing Time" value={report?.total_questions != null ? `${report.total_questions} questions` : "N/A"} icon={Clock} color="hsl(var(--chart-2))" subtitle="Evaluation dataset size" />
                <KnowledgeCard label="Total Chunks" value={totalChunks?.toLocaleString() ?? "N/A"} icon={BookOpen} color="hsl(var(--chart-3))" subtitle="Indexed knowledge pieces" />
                <KnowledgeCard label="Total Pages" value={totalPages?.toLocaleString() ?? "N/A"} icon={FileText} color="hsl(var(--chart-4))" subtitle="Across all documents" />
              </div>
            </div>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <BarChart3 className="h-4 w-4 text-primary" />
                  Quality Metrics Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <MetricBar value={faithfulness != null ? faithfulness * 100 : 0} label="Faithfulness" icon={Shield} color="hsl(var(--success))" />
                <MetricBar value={correctness != null ? correctness * 100 : 0} label="Correctness" icon={CheckCircle2} color="hsl(var(--chart-1))" />
                <MetricBar value={relevancy != null ? relevancy * 100 : 0} label="Answer Relevancy" icon={Target} color="hsl(var(--chart-2))" />
                <MetricBar value={recall != null ? recall * 100 : 0} label="Context Recall" icon={BookOpen} color="hsl(var(--chart-3))" />
                <MetricBar value={precision != null ? precision * 100 : 0} label="Context Precision" icon={Gauge} color="hsl(var(--chart-4))" />
                <Separator />
                <MetricBar value={retrySuccess != null ? (1 - retrySuccess) * 100 : 0} label="Retry Rate" icon={RefreshCw} color="hsl(var(--warning))" />
              </CardContent>
            </Card>

            <Tabs defaultValue="comparison" className="mt-2">
              <TabsList>
                <TabsTrigger value="comparison" disabled={!c}>
                  <TrendingUp className="mr-2 h-4 w-4" />
                  vs Baseline
                </TabsTrigger>
                <TabsTrigger value="history" disabled={historyLoading}>
                  <History className="mr-2 h-4 w-4" />
                  History
                </TabsTrigger>
              </TabsList>

              <TabsContent value="comparison" className="mt-6">
                {c ? (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <TrendingUp className="h-4 w-4 text-primary" />
                        Comparison vs Baseline
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {Object.entries(c).map(([key, val]) => {
                          const v = val as { baseline?: number; sentinel?: number; absolute_change?: number; relative_change_pct?: number; improved?: boolean };
                          const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                          return (
                            <div key={key} className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-secondary/30 transition-colors">
                              <span className="text-sm font-medium">{label}</span>
                              <div className="flex items-center gap-3">
                                <span className="text-xs text-muted-foreground">Baseline: {v.baseline != null ? `${(v.baseline * 100).toFixed(1)}%` : "--"}</span>
                                <Badge variant={v.improved ? "success" : "destructive"} className="text-[10px] px-1.5 py-0">
                                  {v.improved ? "▲" : "▼"} {v.absolute_change != null ? `${(Math.abs(v.absolute_change) * 100).toFixed(1)}%` : "--"}
                                </Badge>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <EmptyState icon={TrendingUp} title="No Comparison Data" description="Run an evaluation with a baseline to see comparisons." />
                )}
              </TabsContent>

              <TabsContent value="history" className="mt-6">
                {historyLoading ? (
                  <LoadingSkeleton type="table" count={3} />
                ) : history && history.length > 0 ? (
                  <div className="space-y-2">
                    {history.map((item, i) => (
                      <div key={item.evaluation_id ?? i} className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-secondary/30">
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                            <BarChart3 className="h-4 w-4 text-primary" />
                          </div>
                          <div>
                            <p className="text-sm font-medium">Evaluation Run #{i + 1}</p>
                            <p className="text-xs text-muted-foreground">
                              {item.timestamp ? new Date(item.timestamp).toLocaleString() : "Unknown date"}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-[10px]">{item.total_questions ?? "?"} questions</Badge>
                          <Badge variant="outline" className="text-[10px]">{item.dataset ?? "benchmark"}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState icon={History} title="No Evaluation History" description="Run an evaluation to see history here." />
                )}
              </TabsContent>
            </Tabs>
          </>
        ) : (
          <EmptyState
            icon={BarChart3}
            title="No Evaluation Data"
            description="Run an evaluation to measure your RAG pipeline performance across faithfulness, correctness, retrieval accuracy, and more."
            action={
              <Button onClick={handleRun} disabled={runEval.isPending} size="lg" className="gap-2">
                {runEval.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Run Evaluation
              </Button>
            }
          />
        )}
      </div>
    </ErrorBoundary>
  );
}
