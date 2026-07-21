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
  Database,
  Shield,
  Activity,
  Clock,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

export default function DashboardPage() {
  const { data: health, isLoading: healthLoading } = useHealth();
  const { data: documents, isLoading: docsLoading } = useDocuments();
  const { data: evaluation, isLoading: evalLoading } = useEvaluationReport();

  const totalDocs = documents?.length ?? 0;
  const completedDocs = documents?.filter((d) => d.status === "completed").length ?? 0;
  const totalWords = documents?.reduce((sum, d) => sum + (d.word_count || 0), 0) ?? 0;
  const uptime = health?.uptime_seconds ?? 0;
  const uptimeFormatted = uptime > 3600
    ? `${(uptime / 3600).toFixed(1)}h`
    : `${(uptime / 60).toFixed(0)}m`;

  const summary = evaluation?.summary;

  return (
    <ErrorBoundary>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Overview</h1>
          <p className="text-sm text-muted-foreground mt-1">
            System status and key metrics at a glance.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {docsLoading ? (
            <LoadingSkeleton type="card" count={4} />
          ) : (
            <>
              <MetricCard
                title="Total Documents"
                value={totalDocs}
                subtitle={`${completedDocs} processed`}
                icon={FileText}
                color="hsl(var(--chart-1))"
              />
              <MetricCard
                title="Words Indexed"
                value={totalWords.toLocaleString()}
                subtitle="across all documents"
                icon={Brain}
                color="hsl(var(--chart-2))"
              />
              <MetricCard
                title="Uptime"
                value={uptimeFormatted}
                subtitle={health?.status === "healthy" ? "All systems operational" : "Issues detected"}
                icon={Activity}
                color="hsl(var(--chart-3))"
              />
              <MetricCard
                title="Search Queries"
                value="--"
                subtitle="today"
                icon={Search}
                color="hsl(var(--chart-4))"
              />
            </>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Database className="h-4 w-4 text-primary" />
                System Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              {healthLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="flex items-center justify-between rounded-lg bg-secondary/30 p-3">
                      <div className="h-4 w-24 bg-muted rounded animate-pulse" />
                      <div className="h-5 w-16 bg-muted rounded animate-pulse" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-1">
                  <StatusRow label="API Status" status={health?.status ?? "unknown"} />
                  <StatusRow label="PostgreSQL" status={health?.status === "healthy" ? "connected" : "unknown"} />
                  <StatusRow label="Qdrant" status={health?.status === "healthy" ? "connected" : "unknown"} />
                  <StatusRow label="Version" status={health?.version ?? "--"} />
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3Icon className="h-4 w-4 text-primary" />
                Evaluation Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              {evalLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-center justify-between p-3">
                      <div className="h-4 w-32 bg-muted rounded animate-pulse" />
                      <div className="h-4 w-16 bg-muted rounded animate-pulse" />
                    </div>
                  ))}
                </div>
              ) : summary ? (
                <div className="space-y-2">
                  <EvalRow label="Faithfulness" value={summary.sentinel?.faithfulness?.value} />
                  <EvalRow label="Answer Relevancy" value={summary.sentinel?.answer_relevancy?.value} />
                  <EvalRow label="Context Precision" value={summary.sentinel?.context_precision?.value} />
                  <EvalRow label="Context Recall" value={summary.sentinel?.context_recall?.value} />
                  <EvalRow label="Correctness" value={summary.sentinel?.correctness?.value} />
                </div>
              ) : (
                <div className="flex flex-col items-center py-8 text-center">
                  <AlertTriangle className="h-8 w-8 text-muted-foreground mb-3" />
                  <p className="text-sm text-muted-foreground">No evaluation data yet.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

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
            ) : documents && documents.length > 0 ? (
              <div className="space-y-2">
                {documents.slice(0, 5).map((doc) => (
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
                          {doc.word_count?.toLocaleString() ?? 0} words · {new Date(doc.created_at).toLocaleDateString()}
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

function BarChart3Icon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="12" y1="20" x2="12" y2="10" />
      <line x1="18" y1="20" x2="18" y2="4" />
      <line x1="6" y1="20" x2="6" y2="16" />
    </svg>
  );
}
