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
import toast from "react-hot-toast";
import {
  BarChart3,
  Play,
  History,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  Loader2,
} from "lucide-react";

export default function EvaluationPage() {
  const { data: report, isLoading: reportLoading } = useEvaluationReport();
  const { data: history, isLoading: historyLoading } = useEvaluationHistory();
  const runEval = useRunEvaluation();
  const [chartTab, setChartTab] = useState("metrics");

  const handleRun = async () => {
    try {
      await runEval.mutateAsync();
      toast.success("Evaluation completed");
    } catch {
      toast.error("Evaluation failed");
    }
  };

  const summary = report?.summary;

  const metricKeys = summary?.sentinel
    ? Object.entries(summary.sentinel)
        .filter(([k]) => k !== "timestamp" && k !== "dataset")
        .map(([k, v]) => ({
          key: k,
          label: k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
          value: typeof v === "object" && v !== null ? (v as { value?: number }).value : undefined,
        }))
    : [];

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
          <Button onClick={handleRun} disabled={runEval.isPending}>
            {runEval.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Run Evaluation
          </Button>
        </div>

        <Tabs value={chartTab} onValueChange={setChartTab}>
          <TabsList>
            <TabsTrigger value="metrics">
              <BarChart3 className="mr-2 h-4 w-4" />
              Metrics
            </TabsTrigger>
            <TabsTrigger value="history" disabled={historyLoading}>
              <History className="mr-2 h-4 w-4" />
              History
            </TabsTrigger>
          </TabsList>

          <TabsContent value="metrics" className="mt-6">
            {reportLoading ? (
              <LoadingSkeleton type="card" count={3} />
            ) : metricKeys.length > 0 ? (
              <div className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {metricKeys.map((metric, i) => (
                    <motion.div
                      key={metric.key}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                    >
                      <Card>
                        <CardContent className="pt-6">
                          <p className="text-sm text-muted-foreground">{metric.label}</p>
                          <div className="mt-2 flex items-baseline gap-2">
                            <span className="text-2xl font-bold">
                              {metric.value !== undefined
                                ? `${(metric.value * 100).toFixed(1)}%`
                                : "--"}
                            </span>
                            <Badge
                              variant={
                                metric.value !== undefined && metric.value >= 0.8
                                  ? "success"
                                  : metric.value !== undefined && metric.value >= 0.5
                                  ? "warning"
                                  : "destructive"
                              }
                            >
                              {metric.value !== undefined
                                ? metric.value >= 0.8
                                  ? "Excellent"
                                  : metric.value >= 0.5
                                  ? "Good"
                                  : "Needs Work"
                                : "N/A"}
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </div>

                {summary?.comparison && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <TrendingUp className="h-4 w-4 text-primary" />
                        vs Baseline
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {Object.entries(summary.comparison).map(([key, val]) => {
                          const v = val as { improvement?: string; absolute_change?: number };
                          const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                          const improved = v.improvement === "yes" || (v.absolute_change ?? 0) > 0;
                          return (
                            <div
                              key={key}
                              className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-secondary/30 transition-colors"
                            >
                              <span className="text-sm">{label}</span>
                              <div className="flex items-center gap-2">
                                {improved ? (
                                  <CheckCircle2 className="h-4 w-4 text-success" />
                                ) : (
                                  <AlertTriangle className="h-4 w-4 text-warning" />
                                )}
                                <span className="text-sm font-medium">
                                  {v.absolute_change !== undefined
                                    ? `${(v.absolute_change * 100).toFixed(1)}%`
                                    : "--"}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            ) : (
              <EmptyState
                icon={BarChart3}
                title="No evaluation data"
                description="Run an evaluation to see how your pipeline performs."
                action={
                  <Button onClick={handleRun} disabled={runEval.isPending}>
                    {runEval.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    Run Evaluation
                  </Button>
                }
              />
            )}
          </TabsContent>

          <TabsContent value="history" className="mt-6">
            {historyLoading ? (
              <LoadingSkeleton type="table" count={3} />
            ) : history && history.length > 0 ? (
              <div className="space-y-2">
                {history.map((item, i) => (
                  <div
                    key={item.evaluation_id ?? i}
                    className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-secondary/30"
                  >
                    <div>
                      <p className="text-sm font-medium">
                        Run #{i + 1}
                      </p>
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
              <EmptyState
                icon={History}
                title="No evaluation history"
                description="Run an evaluation to see history here."
              />
            )}
          </TabsContent>
        </Tabs>
      </div>
    </ErrorBoundary>
  );
}
