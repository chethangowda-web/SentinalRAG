"use client";

import { useHealth } from "@/hooks/use-health";
import { useDocuments } from "@/hooks/use-documents";
import { useEvaluationReport } from "@/hooks/use-evaluation";
import { MetricCard } from "@/components/shared/MetricCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Brain,
  Search,
  Activity,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Shield,
  Zap,
  Gauge,
  BarChart3,
} from "lucide-react";
import type { IngestResponse } from "@/types";

export default function DashboardPage() {
  const { data: health, isLoading: healthLoading } = useHealth();
  const { data: documents, isLoading: docsLoading } = useDocuments();
  const { data: evaluation, isLoading: evalLoading } = useEvaluationReport();

  const totalDocs = documents?.length ?? 0;
  const totalChunks = documents?.reduce((sum, d) => sum + (d.chunk_count || 0), 0) ?? 0;
  const totalWords = documents?.reduce((sum, d) => sum + (d.word_count || 0), 0) ?? 0;
  const uptime = health?.uptime_seconds ?? 0;
  const uptimeFormatted = uptime > 3600
    ? `${(uptime / 3600).toFixed(1)}h`
    : `${(uptime / 60).toFixed(0)}m`;

  const summary = evaluation?.summary;
  const faithfulness = summary?.sentinel?.faithfulness?.value;
  const avgConfidence = summary?.sentinel?.answer_relevancy?.value;
  const hallucinationRate = faithfulness != null ? ((1 - faithfulness) * 100).toFixed(1) : null;

  const recentDocs = documents?.slice(0, 5) ?? [];

  return (
    <ErrorBoundary>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">RAG Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time retrieval-augmented generation performance metrics.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Documents Indexed"
            value={totalDocs}
            subtitle="total documents"
            icon={FileText}
            color="hsl(var(--chart-1))"
          />
          <MetricCard
            title="Chunks Created"
            value={totalChunks.toLocaleString()}
            subtitle={`${totalWords.toLocaleString()} words`}
            icon={Brain}
            color="hsl(var(--chart-2))"
          />
          <MetricCard
            title="Embeddings Stored"
            value={totalChunks.toLocaleString()}
            subtitle="384-dimensional vectors"
            icon={BarChart3}
            color="hsl(var(--chart-3))"
          />
          <MetricCard
            title="Average Retrieval"
            value={avgConfidence != null ? `${(avgConfidence * 100).toFixed(0)}%` : "--"}
            subtitle="confidence score"
            icon={Search}
            color="hsl(var(--chart-4))"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Hallucination Rate"
            value={hallucinationRate != null ? `${hallucinationRate}%` : "--"}
            subtitle="of generated answers"
            icon={AlertTriangle}
            color="hsl(var(--chart-1))"
          />
          <MetricCard
            title="Self-Corrections"
            value={summary?.sentinel?.retry_rate?.value != null ? `${(summary.sentinel.retry_rate.value * 100).toFixed(0)}%` : "--"}
            subtitle="query rewrites triggered"
            icon={RefreshCw}
            color="hsl(var(--chart-2))"
          />
          <MetricCard
            title="Average Confidence"
            value={faithfulness != null ? `${(faithfulness * 100).toFixed(0)}%` : "--"}
            subtitle="faithfulness score"
            icon={Shield}
            color="hsl(var(--chart-3))"
          />
          <MetricCard
            title="System Uptime"
            value={uptimeFormatted}
            subtitle={health?.status === "healthy" ? "All systems operational" : "Issues detected"}
            icon={Activity}
            color="hsl(var(--chart-4))"
          />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="h-4 w-4 text-primary" />
                Evaluation Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              {evalLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="flex items-center justify-between p-3">
                      <div className="h-4 w-32 bg-muted rounded animate-pulse" />
                      <div className="h-4 w-16 bg-muted rounded animate-pulse" />
                    </div>
                  ))}
                </div>
              ) : summary ? (
                <div className="space-y-2">
                  <EvalRow label="Faithfulness" value={summary.sentinel?.faithfulness?.value} />
                  <EvalRow label="Correctness" value={summary.sentinel?.correctness?.value} />
                  <EvalRow label="Answer Relevancy" value={summary.sentinel?.answer_relevancy?.value} />
                  <EvalRow label="Context Recall" value={summary.sentinel?.context_recall?.value} />
                  <EvalRow label="Context Precision" value={summary.sentinel?.context_precision?.value} />
                </div>
              ) : (
                <div className="flex flex-col items-center py-8 text-center">
                  <AlertTriangle className="h-8 w-8 text-muted-foreground mb-3" />
                  <p className="text-sm text-muted-foreground">No evaluation data yet. Run an evaluation to see metrics.</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock className="h-4 w-4 text-primary" />
                Recent Documents
              </CardTitle>
            </CardHeader>
            <CardContent>
              {docsLoading ? (
                <LoadingSkeleton type="table" count={3} />
              ) : recentDocs.length > 0 ? (
                <div className="space-y-2">
                  {recentDocs.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-secondary/30"
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                          <FileText className="h-4 w-4 text-primary" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{doc.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {doc.chunk_count ?? 0} chunks · {doc.word_count?.toLocaleString() ?? 0} words · {new Date(doc.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <StatusBadge status={doc.status} />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center py-8 text-center">
                  <FileText className="h-8 w-8 text-muted-foreground mb-3" />
                  <p className="text-sm text-muted-foreground">No documents yet. Upload your first document to get started.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ErrorBoundary>
  );
}

function StatusRow({ label, status }: { label: string; status: string }) {
  const isHealthy = status === "healthy" || status === "connected";
  return (
    <div className="flex items-center justify-between rounded-lg px-3 py-2.5 hover:bg-secondary/30 transition-colors">
      <span className="text-sm">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground capitalize">{status}</span>
        {isHealthy ? (
          <CheckCircle2 className="h-4 w-4 text-success" />
        ) : (
          <AlertTriangle className="h-4 w-4 text-warning" />
        )}
      </div>
    </div>
  );
}

function EvalRow({ label, value }: { label: string; value?: number | string }) {
  if (value === undefined || value === null) return null;
  const numeric = typeof value === "string" ? parseFloat(value) : value;
  return (
    <div className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-secondary/30 transition-colors">
      <span className="text-sm">{label}</span>
      <Badge variant={numeric >= 80 ? "success" : numeric >= 50 ? "warning" : "destructive"}>
        {typeof value === "number" ? `${(value * 100).toFixed(1)}%` : value}
      </Badge>
    </div>
  );
}
