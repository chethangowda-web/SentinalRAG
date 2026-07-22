"use client";

import { useHealth } from "@/hooks/use-health";
import { useDocuments } from "@/hooks/use-documents";
import { useEvaluationReport } from "@/hooks/use-evaluation";
import { useDashboardStats } from "@/hooks/use-dashboard";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import {
  FileText,
  MessageSquare,
  Shield,
  Clock,
  RefreshCw,
  Scan,
  Target,
  Activity,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Sparkles,
  Gauge,
  BookOpen,
  Layers,
  Minus,
  Zap,
  Brain,
} from "lucide-react";

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  href,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  color: string;
  href?: string;
}) {
  const content = (
    <div className="group relative overflow-hidden rounded-xl border bg-card p-5 transition-all duration-200 hover:shadow-md hover:border-primary/20 h-full">
      <div className="absolute inset-0 opacity-[0.02] transition-opacity group-hover:opacity-[0.05]" style={{ background: `linear-gradient(135deg, ${color} 0%, transparent 100%)` }} />
      <div className="relative flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground font-medium">{title}</p>
          <p className="text-2xl font-bold tracking-tight">{value}</p>
          {subtitle && (
            <p className="text-[10px] text-muted-foreground">{subtitle}</p>
          )}
        </div>
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-background" style={{ backgroundColor: `${color}10` }}>
          <Icon className="h-5 w-5" style={{ color }} />
        </div>
      </div>
      {href && (
        <div className="mt-3 flex items-center gap-1 text-[10px] font-medium" style={{ color }}>
          View details
          <ArrowRight className="h-3 w-3" />
        </div>
      )}
    </div>
  );

  if (href) {
    return <Link href={href} className="block">{content}</Link>;
  }
  return content;
}

function HealthBadge({ status }: { status: string }) {
  if (status === "healthy") return <Badge variant="success" className="gap-1.5 text-[10px]"><CheckCircle2 className="h-3 w-3" />Healthy</Badge>;
  if (status === "degraded") return <Badge variant="warning" className="gap-1.5 text-[10px]"><AlertTriangle className="h-3 w-3" />Degraded</Badge>;
  if (status === "unhealthy") return <Badge variant="destructive" className="gap-1.5 text-[10px]"><XCircle className="h-3 w-3" />Unhealthy</Badge>;
  return <Badge variant="outline" className="gap-1.5 text-[10px]"><Minus className="h-3 w-3" />Unknown</Badge>;
}

export default function DashboardPage() {
  const { data: health, isLoading: healthLoading } = useHealth();
  const { data: documents, isLoading: docsLoading } = useDocuments();
  const { data: evaluation } = useEvaluationReport();
  const { data: stats, isLoading: statsLoading } = useDashboardStats();

  const loading = statsLoading || docsLoading || healthLoading;

  const totalDocs = stats?.total_documents ?? documents?.length ?? 0;
  const totalChunks = stats?.total_chunks ?? documents?.reduce((sum, d) => sum + (d.chunk_count || 0), 0) ?? 0;
  const totalSessions = stats?.total_sessions ?? 0;
  const totalPages = stats?.total_pages ?? documents?.reduce((sum, d) => sum + (d.pages || 0), 0) ?? 0;
  const uptime = health?.uptime_seconds ?? 0;
  const uptimeFormatted = uptime > 3600 ? `${(uptime / 3600).toFixed(1)}h` : `${(uptime / 60).toFixed(0)}m`;

  const summary = evaluation?.summary;
  const s = summary?.sentinel;
  const faithfulness = s?.avg_faithfulness?.value;
  const correctness = s?.avg_correctness?.value;
  const relevancy = s?.avg_answer_relevancy?.value;
  const recall = s?.avg_context_recall?.value;
  const precision = s?.avg_context_precision?.value;
  const retrySuccess = s?.retry_success_rate?.value;

  const allValues = [faithfulness, correctness, relevancy, recall, precision].filter((v): v is number => v != null);
  const avgConfidence = allValues.length > 0 ? (allValues.reduce((a, b) => a + b, 0) / allValues.length) * 100 : null;
  const retrievalAccuracy = recall != null && precision != null ? ((recall + precision) / 2) * 100 : null;
  const selfCorrectionRate = retrySuccess != null ? (1 - retrySuccess) * 100 : null;
  const ocrConfidence = stats?.avg_ocr_confidence != null ? stats.avg_ocr_confidence * 100 : null;

  const recentDocs = stats?.recent_documents ?? documents?.slice(0, 5) ?? [];

  return (
    <ErrorBoundary>
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Real-time overview of your RAG system performance.
            </p>
          </div>
          {!loading && (
            <HealthBadge status={health?.status ?? "unknown"} />
          )}
        </div>

        {loading ? (
          <LoadingSkeleton type="card" count={8} />
        ) : (
          <>
            <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
              <StatCard
                title="Documents Uploaded"
                value={totalDocs}
                subtitle={`${totalPages} pages · ${totalChunks.toLocaleString()} chunks`}
                icon={FileText}
                color="hsl(var(--chart-1))"
                href="/dashboard/documents"
              />
              <StatCard
                title="Questions Asked"
                value={totalSessions}
                subtitle={totalSessions === 1 ? "chat session" : "chat sessions"}
                icon={MessageSquare}
                color="hsl(var(--chart-2))"
                href="/dashboard/chat"
              />
              <StatCard
                title="Average Confidence"
                value={avgConfidence != null ? `${avgConfidence.toFixed(0)}%` : "--"}
                subtitle={avgConfidence != null ? "across all evaluations" : "run evaluation"}
                icon={Shield}
                color={avgConfidence != null && avgConfidence >= 70 ? "hsl(var(--success))" : "hsl(var(--warning))"}
              />
              <StatCard
                title="Avg Response Time"
                value={uptime > 0 ? uptimeFormatted : "--"}
                subtitle="system uptime"
                icon={Clock}
                color="hsl(var(--chart-3))"
              />
              <StatCard
                title="Self-Corrections"
                value={selfCorrectionRate != null ? `${selfCorrectionRate.toFixed(0)}%` : "--"}
                subtitle="query rewrite rate"
                icon={RefreshCw}
                color="hsl(var(--chart-4))"
              />
              <StatCard
                title="OCR Success Rate"
                value={ocrConfidence != null ? `${ocrConfidence.toFixed(0)}%` : "--"}
                subtitle={ocrConfidence != null ? "avg OCR confidence" : "no OCR data"}
                icon={Scan}
                color="hsl(var(--chart-1))"
              />
              <StatCard
                title="Retrieval Accuracy"
                value={retrievalAccuracy != null ? `${retrievalAccuracy.toFixed(0)}%` : "--"}
                subtitle="context recall & precision"
                icon={Target}
                color={retrievalAccuracy != null && retrievalAccuracy >= 70 ? "hsl(var(--success))" : "hsl(var(--warning))"}
              />
              <StatCard
                title="System Health"
                value={health?.status === "healthy" ? "Operational" : health?.status ?? "Unknown"}
                subtitle={health?.version ? `v${health.version}` : ""}
                icon={Activity}
                color={health?.status === "healthy" ? "hsl(var(--success))" : "hsl(var(--destructive))"}
              />
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    Quality Metrics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {s ? (
                    <div className="space-y-3">
                      <EvalRow label="Faithfulness" value={faithfulness} color="hsl(var(--success))" />
                      <EvalRow label="Correctness" value={correctness} color="hsl(var(--chart-1))" />
                      <EvalRow label="Answer Relevancy" value={relevancy} color="hsl(var(--chart-2))" />
                      <EvalRow label="Context Recall" value={recall} color="hsl(var(--chart-3))" />
                      <EvalRow label="Context Precision" value={precision} color="hsl(var(--chart-4))" />
                    </div>
                  ) : (
                    <div className="flex flex-col items-center py-8 text-center">
                      <BarChart3 className="h-8 w-8 text-muted-foreground/50 mb-3" />
                      <p className="text-sm text-muted-foreground">No evaluation data yet.</p>
                      <Link href="/dashboard/evaluation">
                        <Button variant="outline" size="sm" className="mt-3">
                          <BarChart3 className="mr-2 h-4 w-4" />
                          Run Evaluation
                        </Button>
                      </Link>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Layers className="h-4 w-4 text-primary" />
                    Document Types
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {stats?.document_types && Object.keys(stats.document_types).length > 0 ? (
                    <div className="space-y-2">
                      {Object.entries(stats.document_types).map(([type, count]) => (
                        <div key={type} className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-secondary/30 transition-colors">
                          <div className="flex items-center gap-2">
                            <BookOpen className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm capitalize">{type.replace(/_/g, " ")}</span>
                          </div>
                          <Badge variant="outline">{count as number}</Badge>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center py-8 text-center">
                      <BookOpen className="h-8 w-8 text-muted-foreground/50 mb-3" />
                      <p className="text-sm text-muted-foreground">No documents categorized yet.</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Clock className="h-4 w-4 text-primary" />
                    Recent Documents
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {recentDocs.length > 0 ? (
                    <div className="space-y-2">
                      {recentDocs.map((doc) => (
                        <Link key={doc.id} href="/dashboard/documents">
                          <div className="flex items-center justify-between rounded-lg border p-3 transition-all hover:border-primary/20 hover:bg-secondary/30">
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                                <FileText className="h-4 w-4 text-primary" />
                              </div>
                              <div className="min-w-0">
                                <p className="text-sm font-medium truncate">{doc.filename}</p>
                                <p className="text-[10px] text-muted-foreground">
                                  {doc.document_type && <span className="capitalize">{doc.document_type.replace(/_/g, " ")}</span>}
                                  {doc.ocr_quality && <span> · OCR: {doc.ocr_quality.replace(/_/g, " ")}</span>}
                                  <span> · {new Date(doc.created_at).toLocaleDateString()}</span>
                                </p>
                              </div>
                            </div>
                            <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
                          </div>
                        </Link>
                      ))}
                      <Link href="/dashboard/documents">
                        <Button variant="ghost" size="sm" className="w-full mt-2 text-xs">
                          View All Documents
                          <ArrowRight className="ml-2 h-3 w-3" />
                        </Button>
                      </Link>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center py-8 text-center">
                      <FileText className="h-8 w-8 text-muted-foreground/50 mb-3" />
                      <p className="text-sm text-muted-foreground">No documents yet.</p>
                      <Link href="/dashboard/upload">
                        <Button variant="outline" size="sm" className="mt-3">
                          <FileText className="mr-2 h-4 w-4" />
                          Upload Document
                        </Button>
                      </Link>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
    </ErrorBoundary>
  );
}

function EvalRow({ label, value, color }: { label: string; value?: number; color: string }) {
  if (value == null) return null;
  const pct = value * 100;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold tabular-nums">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}
