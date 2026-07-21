"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useEvaluationReport, useEvaluationHistory, useRunEvaluation } from "@/hooks/use-evaluation";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/shared/EmptyState";
import { Badge } from "@/components/ui/badge";
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
} from "lucide-react";

function GaugeChart({ value, label, color }: { value: number; label: string; color: string }) {
  const degrees = (value / 100) * 180;
  return (
    <div className="flex flex-col items-center p-4">
      <div className="relative w-24 h-12 overflow-hidden">
        <div className="absolute inset-0 rounded-t-full border-4 border-secondary" />
        <div
          className="absolute inset-0 rounded-t-full border-4 border-transparent origin-bottom"
          style={{
            borderColor: `${color} transparent transparent transparent`,
            transform: `rotate(${degrees}deg)`,
            transition: "transform 1s ease-out",
          }}
        />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-center">
          <span className="text-lg font-bold" style={{ color }}>{value}%</span>
        </div>
      </div>
      <p className="text-xs text-muted-foreground mt-2">{label}</p>
    </div>
  );
}

function Bar({ value, label, max = 100, color = "hsl(var(--primary))" }: { value: number; label: string; max?: number; color?: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value}%</span>
      </div>
      <div className="h-2 rounded-full bg-secondary overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
    </div>
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

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Evaluation</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Benchmark your RAG pipeline against a standard baseline.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {isRunning && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Evaluating {runProgress}/{runTotal} questions...</span>
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

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="pt-6 text-center">
              <Shield className="h-5 w-5 text-success mx-auto mb-2" />
              <p className="text-2xl font-bold">{s?.avg_faithfulness?.value != null ? `${(s.avg_faithfulness.value * 100).toFixed(0)}%` : "--"}</p>
              <p className="text-xs text-muted-foreground">Faithfulness</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <Target className="h-5 w-5 text-primary mx-auto mb-2" />
              <p className="text-2xl font-bold">{s?.avg_correctness?.value != null ? `${(s.avg_correctness.value * 100).toFixed(0)}%` : "--"}</p>
              <p className="text-xs text-muted-foreground">Correctness</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <Activity className="h-5 w-5 text-chart-2 mx-auto mb-2" />
              <p className="text-2xl font-bold">{s?.avg_answer_relevancy?.value != null ? `${(s.avg_answer_relevancy.value * 100).toFixed(0)}%` : "--"}</p>
              <p className="text-xs text-muted-foreground">Answer Relevancy</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <Brain className="h-5 w-5 text-chart-3 mx-auto mb-2" />
              <p className="text-2xl font-bold">{s?.avg_context_recall?.value != null ? `${(s.avg_context_recall.value * 100).toFixed(0)}%` : "--"}</p>
              <p className="text-xs text-muted-foreground">Context Recall</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="pt-6 text-center">
              <CheckCircle2 className="h-5 w-5 text-success mx-auto mb-2" />
              <p className="text-2xl font-bold">{s?.avg_context_precision?.value != null ? `${(s.avg_context_precision.value * 100).toFixed(0)}%` : "--"}</p>
              <p className="text-xs text-muted-foreground">Precision</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <XCircle className="h-5 w-5 text-destructive mx-auto mb-2" />
              <p className="text-2xl font-bold">{s?.avg_faithfulness?.value != null ? `${((1 - s.avg_faithfulness.value) * 100).toFixed(1)}%` : "--"}</p>
              <p className="text-xs text-muted-foreground">Hallucination</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <RefreshCw className="h-5 w-5 text-warning mx-auto mb-2" />
              <p className="text-2xl font-bold">{s?.retry_success_rate?.value != null ? `${((1 - s.retry_success_rate.value) * 100).toFixed(0)}%` : "--"}</p>
              <p className="text-xs text-muted-foreground">Retry Rate</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6 text-center">
              <Activity className="h-5 w-5 text-chart-4 mx-auto mb-2" />
              <p className="text-2xl font-bold">{report?.total_questions != null ? `${report.total_questions}` : "--"}</p>
              <p className="text-xs text-muted-foreground">Questions</p>
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="metrics">
          <TabsList>
            <TabsTrigger value="metrics"><BarChart3 className="mr-2 h-4 w-4" /> Metrics</TabsTrigger>
            <TabsTrigger value="comparison" disabled={!c}><TrendingUp className="mr-2 h-4 w-4" /> vs Baseline</TabsTrigger>
            <TabsTrigger value="history" disabled={historyLoading}><History className="mr-2 h-4 w-4" /> History</TabsTrigger>
          </TabsList>

          <TabsContent value="metrics" className="mt-6">
            {reportLoading ? (
              <LoadingSkeleton type="card" count={3} />
            ) : s ? (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Performance Bars</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Bar value={s.avg_faithfulness?.value != null ? s.avg_faithfulness.value * 100 : 0} label="Faithfulness" color="hsl(var(--success))" />
                    <Bar value={s.avg_correctness?.value != null ? s.avg_correctness.value * 100 : 0} label="Correctness" color="hsl(var(--primary))" />
                    <Bar value={s.avg_answer_relevancy?.value != null ? s.avg_answer_relevancy.value * 100 : 0} label="Answer Relevancy" color="hsl(var(--chart-2))" />
                    <Bar value={s.avg_context_recall?.value != null ? s.avg_context_recall.value * 100 : 0} label="Context Recall" color="hsl(var(--chart-3))" />
                    <Bar value={s.avg_context_precision?.value != null ? s.avg_context_precision.value * 100 : 0} label="Context Precision" color="hsl(var(--chart-4))" />
                    <Separator />
                    <Bar value={s.retry_success_rate?.value != null ? (1 - s.retry_success_rate.value) * 100 : 0} label="Retry Rate" color="hsl(var(--warning))" max={50} />
                  </CardContent>
                </Card>

                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <GaugeChart value={s.avg_faithfulness?.value != null ? s.avg_faithfulness.value * 100 : 0} label="Faithfulness" color="#22c55e" />
                  <GaugeChart value={s.avg_correctness?.value != null ? s.avg_correctness.value * 100 : 0} label="Correctness" color="#3b82f6" />
                  <GaugeChart value={s.avg_context_recall?.value != null ? s.avg_context_recall.value * 100 : 0} label="Context Recall" color="#a855f7" />
                </div>
              </div>
            ) : isRunning ? (
              <div className="flex flex-col items-center py-12 text-center">
                <Loader2 className="h-10 w-10 text-primary animate-spin mb-4" />
                <h3 className="text-lg font-medium">Evaluation in progress</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Processing {runProgress}/{runTotal} questions...
                </p>
                <div className="w-64 h-2 bg-secondary rounded-full mt-4 overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all duration-500"
                    style={{ width: `${(runProgress / runTotal) * 100}%` }}
                  />
                </div>
              </div>
            ) : (
              <EmptyState
                icon={BarChart3}
                title="No evaluation data"
                description="Run an evaluation to see how your pipeline performs."
                action={
                  <Button onClick={handleRun} disabled={runEval.isPending}>
                    {runEval.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
                    Run Evaluation
                  </Button>
                }
              />
            )}
          </TabsContent>

          <TabsContent value="comparison" className="mt-6">
            {c ? (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <TrendingUp className="h-4 w-4 text-primary" />
                    vs Baseline
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Object.entries(c).map(([key, val]) => {
                      const v = val as { baseline?: number; sentinel?: number; absolute_change?: number; relative_change_pct?: number; improved?: boolean };
                      const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                      return (
                        <div key={key} className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-secondary/30 transition-colors">
                          <span className="text-sm">{label}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-muted-foreground">Baseline: {v.baseline != null ? `${(v.baseline * 100).toFixed(1)}%` : "--"}</span>
                            <span className="text-sm font-medium">{(v.sentinel ?? 0) * 100 > (v.baseline ?? 0) * 100 ? "▲" : "▼"} {(Math.abs(v.absolute_change ?? 0) * 100).toFixed(1)}%</span>
                            {v.improved ? <CheckCircle2 className="h-4 w-4 text-success" /> : <AlertTriangle className="h-4 w-4 text-warning" />}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <EmptyState icon={TrendingUp} title="No comparison data" description="Run an evaluation with a baseline to see comparisons." />
            )}
          </TabsContent>

          <TabsContent value="history" className="mt-6">
            {historyLoading ? (
              <LoadingSkeleton type="table" count={3} />
            ) : history && history.length > 0 ? (
              <div className="space-y-2">
                {history.map((item, i) => (
                  <div key={item.evaluation_id ?? i} className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-secondary/30">
                    <div>
                      <p className="text-sm font-medium">Run #{i + 1}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.timestamp ? new Date(item.timestamp).toLocaleString() : "Unknown date"}
                        {item.total_questions ? ` · ${item.total_questions} questions` : ""}
                      </p>
                    </div>
                    <Badge variant="secondary">{item.dataset ?? "benchmark"}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState icon={History} title="No evaluation history" description="Run an evaluation to see history here." />
            )}
          </TabsContent>
        </Tabs>
      </div>
    </ErrorBoundary>
  );
}
