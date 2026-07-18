"use client";

import { useHealth } from "@/hooks/use-health";
import { useDocuments } from "@/hooks/use-documents";
import { useEvaluationReport } from "@/hooks/use-evaluation";
import { MetricCard } from "@/components/shared/MetricCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import {
  Activity,
  FileText,
  Layers,
  Database,
  Brain,
  MessageSquare,
  Shield,
  TrendingUp,
  AlertCircle,
} from "lucide-react";

function DashboardContent() {
  const { data: health, isLoading: healthLoading, error: healthError } = useHealth();
  const { data: documents, isLoading: docsLoading } = useDocuments();
  const { data: evaluation } = useEvaluationReport();

  const totalChunks = documents?.reduce((acc, d) => acc + (d.pages || 0) * 5, 0) || 0;
  const completedDocs = documents?.filter((d) => d.status === "completed").length || 0;
  const failedDocs = documents?.filter((d) => d.status === "failed").length || 0;

  const latencyAvg = evaluation?.summary?.sentinel?.latency?.value;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">SentinelRAG system overview and performance metrics</p>
        </div>
        {health && <StatusBadge status={health.status} />}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="System Status"
          value={healthLoading ? "..." : healthError ? "Offline" : health?.status || "Unknown"}
          subtitle={health?.version ? `v${health.version}` : undefined}
          icon={Shield}
          color={healthError ? "red" : "emerald"}
        />
        <MetricCard
          title="Documents"
          value={docsLoading ? "..." : documents?.length || 0}
          subtitle={`${completedDocs} completed, ${failedDocs} failed`}
          icon={FileText}
          color="primary"
        />
        <MetricCard
          title="Indexed Chunks"
          value={totalChunks.toLocaleString()}
          subtitle="Across all documents"
          icon={Layers}
          color="blue"
        />
        <MetricCard
          title="Avg Latency"
          value={latencyAvg ? `${latencyAvg.toFixed(0)}ms` : "---"}
          subtitle="Per query"
          icon={Activity}
          color={latencyAvg && latencyAvg < 500 ? "emerald" : "amber"}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold">System Components</h3>
          <div className="space-y-3">
            {[
              { name: "Qdrant Vector DB", status: "healthy", desc: "Collection: documents" },
              { name: "Embedding Model", status: "healthy", desc: "BAAI/bge-small-en-v1.5" },
              { name: "LLM Backend", status: health?.status === "healthy" ? "healthy" : "error", desc: "DeepSeek V4" },
              { name: "PostgreSQL", status: "healthy", desc: "Document metadata store" },
            ].map((comp) => (
              <div key={comp.name} className="flex items-center justify-between rounded-lg bg-secondary/50 p-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-background">
                    {comp.status === "healthy" ? (
                      <Database className="h-4 w-4 text-emerald-500" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium">{comp.name}</p>
                    <p className="text-xs text-muted-foreground">{comp.desc}</p>
                  </div>
                </div>
                <StatusBadge status={comp.status} />
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold">Recent Activity</h3>
          {documents && documents.length > 0 ? (
            <div className="space-y-2">
              {documents.slice(0, 5).map((doc) => (
                <div key={doc.id} className="flex items-center justify-between rounded-lg bg-secondary/50 p-3">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">{doc.filename}</span>
                  </div>
                  <StatusBadge status={doc.status} />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center py-8 text-center">
              <FileText className="mb-2 h-8 w-8 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">No documents uploaded yet</p>
            </div>
          )}
        </div>
      </div>

      {evaluation && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold">Latest Evaluation Summary</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Hallucination Rate"
              value={evaluation.summary?.sentinel?.avg_hallucination ? `${(evaluation.summary.sentinel.avg_hallucination.value * 100).toFixed(1)}%` : "---"}
              icon={AlertCircle}
              color="red"
              trend={evaluation.summary?.comparison?.avg_hallucination ? {
                value: Math.abs(evaluation.summary.comparison.avg_hallucination.relative_change_pct),
                positive: evaluation.summary.comparison.avg_hallucination.improved,
              } : undefined}
            />
            <MetricCard
              title="Faithfulness"
              value={evaluation.summary?.sentinel?.avg_faithfulness ? (evaluation.summary.sentinel.avg_faithfulness.value * 100).toFixed(1) + "%" : "---"}
              icon={Brain}
              color="emerald"
              trend={evaluation.summary?.comparison?.avg_faithfulness ? {
                value: Math.abs(evaluation.summary.comparison.avg_faithfulness.relative_change_pct),
                positive: evaluation.summary.comparison.avg_faithfulness.improved,
              } : undefined}
            />
            <MetricCard
              title="Answer Relevancy"
              value={evaluation.summary?.sentinel?.avg_answer_relevancy ? (evaluation.summary.sentinel.avg_answer_relevancy.value * 100).toFixed(1) + "%" : "---"}
              icon={MessageSquare}
              color="blue"
            />
            <MetricCard
              title="Latency (Avg)"
              value={evaluation.summary?.sentinel?.latency ? `${(evaluation.summary.sentinel.latency.details?.average_ms as number)?.toFixed(0)}ms` : "---"}
              icon={Activity}
              color="purple"
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ErrorBoundary>
      <DashboardContent />
    </ErrorBoundary>
  );
}
