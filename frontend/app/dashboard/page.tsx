"use client";

import { useHealth } from "@/hooks/use-health";
import { useDocuments } from "@/hooks/use-documents";
import { useEvaluationReport } from "@/hooks/use-evaluation";
import { useDashboardStats } from "@/hooks/use-dashboard";
import { MetricCard } from "@/components/shared/MetricCard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Search,
  Activity,
  Clock,
  AlertTriangle,
  RefreshCw,
  Shield,
  BarChart3,
  Scan,
  Layers,
} from "lucide-react";

export default function DashboardPage() {
  const { data: health } = useHealth();
  const { data: documents, isLoading: docsLoading } = useDocuments();
  const { data: evaluation } = useEvaluationReport();
  const { data: stats } = useDashboardStats();

  const totalDocs = stats?.total_documents ?? documents?.length ?? 0;
  const totalChunks = stats?.total_chunks ?? documents?.reduce((sum, d) => sum + (d.chunk_count || 0), 0) ?? 0;
  const totalWords = stats?.total_words ?? documents?.reduce((sum, d) => sum + (d.word_count || 0), 0) ?? 0;
  const totalSessions = stats?.total_sessions ?? 0;
  const uptime = health?.uptime_seconds ?? 0;
  const uptimeFormatted = uptime > 3600 ? `${(uptime / 3600).toFixed(1)}h` : `${(uptime / 60).toFixed(0)}m`;

  const avgOcrConf = stats?.avg_ocr_confidence;
  const docTypes = stats?.document_types ?? {};

  const summary = evaluation?.summary;
  const faithfulness = summary?.sentinel?.avg_faithfulness?.value;
  const avgRelevancy = summary?.sentinel?.avg_answer_relevancy?.value;
  const hallucinationRate = faithfulness != null ? ((1 - faithfulness) * 100).toFixed(1) : null;
  const retryRate = summary?.sentinel?.retry_success_rate?.value;

  const recentDocs = stats?.recent_documents ?? documents?.slice(0, 5) ?? [];

  return (
    <ErrorBoundary>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Document Intelligence Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time metrics for your RAG system.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Documents Indexed"
            value={totalDocs}
            subtitle={`${totalPages(totalDocs, stats)} pages · ${totalWords.toLocaleString()} words`}
            icon={FileText}
            color="hsl(var(--chart-1))"
          />
          <MetricCard
            title="Knowledge Chunks"
            value={totalChunks.toLocaleString()}
            subtitle={`${totalSessions} chat sessions`}
            icon={Layers}
            color="hsl(var(--chart-2))"
          />
          <MetricCard
            title="OCR Confidence"
            value={avgOcrConf != null ? `${avgOcrConf.toFixed(0)}%` : "--"}
            subtitle={avgOcrConf != null ? "average quality score" : "no OCR data"}
            icon={Scan}
            color="hsl(var(--chart-3))"
          />
          <MetricCard
            title="Answer Relevancy"
            value={avgRelevancy != null ? `${(avgRelevancy * 100).toFixed(0)}%` : "--"}
            subtitle="retrieval confidence"
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
            color={hallucinationRate != null && parseFloat(hallucinationRate) > 10 ? "hsl(var(--destructive))" : "hsl(var(--chart-1))"}
          />
          <MetricCard
            title="Self-Corrections"
            value={retryRate != null ? `${((1 - retryRate) * 100).toFixed(0)}%` : "--"}
            subtitle="query rewrites triggered"
            icon={RefreshCw}
            color="hsl(var(--chart-2))"
          />
          <MetricCard
            title="Faithfulness"
            value={faithfulness != null ? `${(faithfulness * 100).toFixed(0)}%` : "--"}
            subtitle="overall answer quality"
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

        <div className="grid gap-6 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="h-4 w-4 text-primary" />
                Document Types
              </CardTitle>
            </CardHeader>
            <CardContent>
              {Object.keys(docTypes).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(docTypes).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between py-1.5">
                      <span className="text-sm capitalize">{type.replace(/_/g, " ")}</span>
                      <Badge variant="outline">{count}</Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-4 text-center">No documents categorized yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="h-4 w-4 text-primary" />
                Evaluation Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              {summary ? (
                <div className="space-y-2">
                  <EvalRow label="Faithfulness" value={summary.sentinel?.avg_faithfulness?.value} />
                  <EvalRow label="Correctness" value={summary.sentinel?.avg_correctness?.value} />
                  <EvalRow label="Answer Relevancy" value={summary.sentinel?.avg_answer_relevancy?.value} />
                  <EvalRow label="Context Recall" value={summary.sentinel?.avg_context_recall?.value} />
                  <EvalRow label="Context Precision" value={summary.sentinel?.avg_context_precision?.value} />
                </div>
              ) : (
                <div className="flex flex-col items-center py-8 text-center">
                  <AlertTriangle className="h-8 w-8 text-muted-foreground mb-3" />
                  <p className="text-sm text-muted-foreground">No evaluation data yet.</p>
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
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 shrink-0">
                          <FileText className="h-4 w-4 text-primary" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{doc.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {doc.document_type && <span className="capitalize">{doc.document_type.replace(/_/g, " ")}</span>}
                            {doc.ocr_quality && <span> · OCR: {doc.ocr_quality}</span>}
                            <span> · {new Date(doc.created_at).toLocaleDateString()}</span>
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center py-8 text-center">
                  <FileText className="h-8 w-8 text-muted-foreground mb-3" />
                  <p className="text-sm text-muted-foreground">No documents yet.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ErrorBoundary>
  );
}

function totalPages(docCount: number, stats?: any): string {
  if (stats?.total_pages) return `${stats.total_pages} pages`;
  return `${docCount} docs`;
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
