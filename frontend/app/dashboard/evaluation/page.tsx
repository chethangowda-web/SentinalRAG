"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart3,
  RefreshCw,
  Download,
  Brain,
  AlertCircle,
  Target,
  Search,
  Layers,
  Clock,
  CheckCircle,
  Shield,
  FileText,
  Activity,
  MessageSquare,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  LineChart, Line, Legend,
} from "recharts";
import { useEvaluationReport, useEvaluationHistory, useRunEvaluation } from "@/hooks/use-evaluation";
import { MetricCard } from "@/components/shared/MetricCard";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { EmptyState } from "@/components/shared/EmptyState";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import type { EvaluationResult } from "@/types";

const CHART_COLORS = {
  baseline: "hsl(217 33% 40%)",
  sentinel: "hsl(142 76% 36%)",
};

function EvaluationContent() {
  const { data: report, isLoading, error } = useEvaluationReport();
  const { data: history } = useEvaluationHistory();
  const runEval = useRunEvaluation();
  const [chartTab, setChartTab] = useState("comparison");

  const handleRun = async () => {
    try {
      await runEval.mutateAsync();
      toast.success("Evaluation completed!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Evaluation failed");
    }
  };

  const buildComparisonData = (result: EvaluationResult) => {
    const metrics = [
      { key: "avg_faithfulness", label: "Faithfulness" },
      { key: "avg_answer_relevancy", label: "Relevancy" },
      { key: "avg_context_precision", label: "Precision" },
      { key: "avg_context_recall", label: "Recall" },
      { key: "avg_correctness", label: "Correctness" },
      { key: "avg_hallucination", label: "Hallucination" },
    ];
    return metrics.map((m) => ({
      metric: m.label,
      Baseline: result.summary.baseline[m.key]?.value ?? 0,
      SentinelRAG: result.summary.sentinel[m.key]?.value ?? 0,
    }));
  };

  const buildRadarData = (result: EvaluationResult) => {
    const metrics = [
      { key: "avg_faithfulness", label: "Faithfulness" },
      { key: "avg_answer_relevancy", label: "Relevancy" },
      { key: "avg_context_precision", label: "Precision" },
      { key: "avg_context_recall", label: "Recall" },
      { key: "avg_correctness", label: "Correctness" },
    ];
    return metrics.map((m) => ({
      metric: m.label,
      Baseline: result.summary.baseline[m.key]?.value ?? 0,
      SentinelRAG: result.summary.sentinel[m.key]?.value ?? 0,
    }));
  };

  const buildLatencyData = (result: EvaluationResult) => {
    if (!result.per_question) return [];
    return result.per_question.map((q, i) => ({
      question: `Q${i + 1}`,
      Baseline: Object.values(q.baseline.latencies).reduce((a, b) => a + b, 0),
      SentinelRAG: Object.values(q.sentinel.latencies).reduce((a, b) => a + b, 0),
    }));
  };

  const downloadReport = (format: string) => {
    if (report?.reports?.[format]) {
      window.open(report.reports[format], "_blank");
    } else {
      toast.success(`Downloading ${format.toUpperCase()} report...`);
    }
  };

  if (isLoading) return <LoadingSkeleton type="detail" />;
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Evaluation Dashboard</h1>
            <p className="text-sm text-muted-foreground">Compare Baseline RAG vs SentinelRAG performance</p>
          </div>
        </div>
        <EmptyState
          icon={BarChart3}
          title="No evaluation data"
          description="Run an evaluation to compare Baseline RAG vs SentinelRAG performance."
          action={
            <Button onClick={handleRun} disabled={runEval.isPending}>
              {runEval.isPending ? "Running..." : "Run Evaluation"}
            </Button>
          }
        />
      </div>
    );
  }
  if (!report) return null;

  const s = report.summary.sentinel;
  const b = report.summary.baseline;
  const comp = report.summary.comparison;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Evaluation Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            {report.total_questions} questions · {report.dataset} · {new Date(report.timestamp).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-xs text-muted-foreground">
            <div className="h-3 w-3 rounded" style={{ background: CHART_COLORS.baseline }} />
            Baseline
            <div className="ml-2 h-3 w-3 rounded" style={{ background: CHART_COLORS.sentinel }} />
            SentinelRAG
          </div>
          <Button variant="outline" size="sm" onClick={() => downloadReport("json")}>
            <Download className="mr-1.5 h-4 w-4" /> JSON
          </Button>
          <Button variant="outline" size="sm" onClick={() => downloadReport("csv")}>
            <Download className="mr-1.5 h-4 w-4" /> CSV
          </Button>
          <Button variant="outline" size="sm" onClick={() => downloadReport("markdown")}>
            <Download className="mr-1.5 h-4 w-4" /> MD
          </Button>
          <Button onClick={handleRun} disabled={runEval.isPending} size="sm">
            <RefreshCw className={`mr-1.5 h-4 w-4 ${runEval.isPending ? "animate-spin" : ""}`} />
            {runEval.isPending ? "Running..." : "Re-Run"}
          </Button>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Hallucination Rate"
          value={s.avg_hallucination ? `${(s.avg_hallucination.value * 100).toFixed(1)}%` : "---"}
          icon={AlertCircle}
          color="red"
          trend={comp.avg_hallucination ? {
            value: Math.abs(comp.avg_hallucination.relative_change_pct),
            positive: comp.avg_hallucination.improved,
          } : undefined}
        />
        <MetricCard
          title="Faithfulness"
          value={s.avg_faithfulness ? `${(s.avg_faithfulness.value * 100).toFixed(1)}%` : "---"}
          icon={Brain}
          color="emerald"
          trend={comp.avg_faithfulness ? {
            value: Math.abs(comp.avg_faithfulness.relative_change_pct),
            positive: comp.avg_faithfulness.improved,
          } : undefined}
        />
        <MetricCard
          title="Answer Relevancy"
          value={s.avg_answer_relevancy ? `${(s.avg_answer_relevancy.value * 100).toFixed(1)}%` : "---"}
          icon={MessageSquare}
          color="blue"
          trend={comp.avg_answer_relevancy ? {
            value: Math.abs(comp.avg_answer_relevancy.relative_change_pct),
            positive: comp.avg_answer_relevancy.improved,
          } : undefined}
        />
        <MetricCard
          title="Avg Latency"
          value={s.latency ? `${(s.latency.details?.average_ms as number)?.toFixed(0)}ms` : "---"}
          icon={Clock}
          color="purple"
          trend={comp.latency ? {
            value: Math.abs(comp.latency.relative_change_pct),
            positive: comp.latency.improved,
          } : undefined}
        />
      </div>

      {/* Secondary metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Context Precision" value={s.avg_context_precision ? `${(s.avg_context_precision.value * 100).toFixed(1)}%` : "---"} icon={Target} color="blue" />
        <MetricCard title="Context Recall" value={s.avg_context_recall ? `${(s.avg_context_recall.value * 100).toFixed(1)}%` : "---"} icon={Search} color="primary" />
        <MetricCard title="Correctness" value={s.avg_correctness ? `${(s.avg_correctness.value * 100).toFixed(1)}%` : "---"} icon={CheckCircle} color="emerald" />
        <MetricCard title="Unsupported Answer Rate" value={s.avg_unsupported_answer_rate ? `${(s.avg_unsupported_answer_rate.value * 100).toFixed(1)}%` : "---"} icon={Shield} color="amber" />
      </div>

      {/* Charts */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Charts</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={chartTab} onValueChange={setChartTab}>
            <TabsList className="mb-4">
              <TabsTrigger value="comparison">Comparison</TabsTrigger>
              <TabsTrigger value="radar">Radar</TabsTrigger>
              <TabsTrigger value="latency">Latency</TabsTrigger>
            </TabsList>

            <TabsContent value="comparison">
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={buildComparisonData(report)} barGap={4}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 33% 22%)" />
                    <XAxis dataKey="metric" tick={{ fill: "hsl(215 20% 65%)", fontSize: 12 }} />
                    <YAxis tick={{ fill: "hsl(215 20% 65%)", fontSize: 12 }} domain={[0, 1]} />
                    <Tooltip
                      contentStyle={{ background: "hsl(222 47% 14%)", border: "1px solid hsl(217 33% 22%)", borderRadius: "0.5rem" }}
                      labelStyle={{ color: "hsl(210 40% 98%)" }}
                    />
                    <Bar dataKey="Baseline" fill={CHART_COLORS.baseline} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="SentinelRAG" fill={CHART_COLORS.sentinel} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </TabsContent>

            <TabsContent value="radar">
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={buildRadarData(report)}>
                    <PolarGrid stroke="hsl(217 33% 22%)" />
                    <PolarAngleAxis dataKey="metric" tick={{ fill: "hsl(215 20% 65%)", fontSize: 11 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 1]} tick={{ fill: "hsl(215 20% 65%)", fontSize: 10 }} />
                    <Radar name="Baseline" dataKey="Baseline" stroke={CHART_COLORS.baseline} fill={CHART_COLORS.baseline} fillOpacity={0.2} />
                    <Radar name="SentinelRAG" dataKey="SentinelRAG" stroke={CHART_COLORS.sentinel} fill={CHART_COLORS.sentinel} fillOpacity={0.2} />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </TabsContent>

            <TabsContent value="latency">
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={buildLatencyData(report)} barGap={4}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 33% 22%)" />
                    <XAxis dataKey="question" tick={{ fill: "hsl(215 20% 65%)", fontSize: 12 }} />
                    <YAxis tick={{ fill: "hsl(215 20% 65%)", fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{ background: "hsl(222 47% 14%)", border: "1px solid hsl(217 33% 22%)", borderRadius: "0.5rem" }}
                    />
                    <Bar dataKey="Baseline" fill={CHART_COLORS.baseline} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="SentinelRAG" fill={CHART_COLORS.sentinel} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Custom Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Custom Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Confidence Calibration", key: "confidence_calibration" },
              { label: "Citation Accuracy", key: "citation_accuracy" },
              { label: "Contradiction Detection", key: "contradiction_detection_rate" },
              { label: "Retry Success Rate", key: "retry_success_rate" },
              { label: "Clarification Rate", key: "clarification_rate" },
            ].map(({ label, key }) => {
              const m = s[key];
              return (
                <div key={key} className="rounded-lg border border-border bg-secondary/30 p-4">
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="mt-1 text-xl font-bold">{m ? `${(m.value * 100).toFixed(1)}%` : "---"}</p>
                </div>
              );
            })}
            <div className="rounded-lg border border-border bg-secondary/30 p-4">
              <p className="text-xs text-muted-foreground">Total Questions</p>
              <p className="mt-1 text-xl font-bold">{report.total_questions}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Evaluation History */}
      {history && history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Evaluation History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {history.map((h) => (
                <div key={h.evaluation_id} className="flex items-center justify-between rounded-lg bg-secondary/50 p-3">
                  <div className="flex items-center gap-2 text-sm">
                    <BarChart3 className="h-4 w-4 text-muted-foreground" />
                    <span>{new Date(h.timestamp).toLocaleString()}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">{h.total_questions} questions</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function EvaluationPage() {
  return (
    <ErrorBoundary>
      <EvaluationContent />
    </ErrorBoundary>
  );
}
