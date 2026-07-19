"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Eye,
  Download,
  FileJson,
  FileText,
  Table,
  ArrowLeft,
  GitBranch,
  Layers,
  PieChart,
  ListChecks,
  Cpu,
  Clock,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Shield,
  BarChart3,
  Network,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RePieChart, Pie, Cell, Legend,
} from "recharts";
import { fetchTraces, fetchTrace, getExportUrl } from "@/services/traces";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { LatencyBadge } from "@/components/shared/LatencyBadge";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { Trace, GraphExecutionRecord, RetrievalDetail, ConfidenceBreakdown } from "@/types";

const PIE_COLORS = ["hsl(142,76%,36%)", "hsl(217,33%,40%)", "hsl(38,92%,50%)", "hsl(271,81%,56%)", "hsl(0,84%,60%)"];

function TraceDetail({ trace, onBack }: { trace: Trace; onBack: () => void }) {
  const [tab, setTab] = useState("timeline");

  const totalLatency = Object.values(trace.latencies).reduce((a, b) => a + b, 0);

  const latencyData = Object.entries(trace.latencies).map(([key, val]) => ({
    name: key.replace(/_/g, " "),
    value: Math.round(val),
  }));

  const confidencePieData = trace.confidence_breakdown
    ? [
        { name: "Vector Similarity", value: Math.round((trace.confidence_breakdown.vector_contribution / (trace.confidence_breakdown.final_score || 1)) * 100) },
        { name: "Cross Encoder", value: Math.round((trace.confidence_breakdown.cross_encoder_contribution / (trace.confidence_breakdown.final_score || 1)) * 100) },
        { name: "Coverage", value: Math.round((trace.confidence_breakdown.coverage_contribution / (trace.confidence_breakdown.final_score || 1)) * 100) },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold">Trace Detail</h2>
            <ConfidenceBadge level={trace.final_confidence_level as any} score={trace.final_confidence} />
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            ID: {trace.id} &middot; {new Date(trace.timestamp).toLocaleString()}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <a href={getExportUrl("json")} target="_blank" rel="noopener"><FileJson className="h-4 w-4 mr-1" />JSON</a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href={getExportUrl("csv")} target="_blank" rel="noopener"><Table className="h-4 w-4 mr-1" />CSV</a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href={getExportUrl("markdown")} target="_blank" rel="noopener"><FileText className="h-4 w-4 mr-1" />MD</a>
          </Button>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="timeline"><GitBranch className="h-4 w-4 mr-1" />Pipeline Timeline</TabsTrigger>
          <TabsTrigger value="decision"><Network className="h-4 w-4 mr-1" />Decision Graph</TabsTrigger>
          <TabsTrigger value="retrieval"><Layers className="h-4 w-4 mr-1" />Retrieval Inspector</TabsTrigger>
          <TabsTrigger value="confidence"><PieChart className="h-4 w-4 mr-1" />Confidence Breakdown</TabsTrigger>
          <TabsTrigger value="latency"><Clock className="h-4 w-4 mr-1" />Latency</TabsTrigger>
          <TabsTrigger value="answer"><FileText className="h-4 w-4 mr-1" />Answer</TabsTrigger>
        </TabsList>

        {/* Pipeline Timeline */}
        <TabsContent value="timeline" className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Execution Timeline</CardTitle></CardHeader>
            <CardContent>
              {trace.session_timeline ? (
                <div className="font-mono text-sm whitespace-pre-wrap rounded-lg bg-secondary/30 p-4">
                  {trace.session_timeline}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No timeline data available.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Graph Node Execution</CardTitle></CardHeader>
            <CardContent>
              {trace.graph_execution.length === 0 ? (
                <p className="text-sm text-muted-foreground">No graph execution data.</p>
              ) : (
                <div className="space-y-3">
                  {trace.graph_execution.map((g, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="rounded-lg border border-border bg-card p-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge variant={i === trace.graph_execution.length - 1 ? "default" : "secondary"}>
                            {g.node_name}
                          </Badge>
                          {g.decision && (
                            <span className="text-xs text-muted-foreground">
                              <ArrowLeft className="h-3 w-3 inline mr-1" />
                              {g.decision}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span>{g.execution_time_ms.toFixed(1)}ms</span>
                          {g.retry_count > 0 && <Badge variant="outline">retry #{g.retry_count}</Badge>}
                        </div>
                      </div>
                      {g.input && (
                        <p className="mt-2 text-xs text-muted-foreground">
                          <span className="font-medium">In:</span> {g.input}
                        </p>
                      )}
                      {g.output && (
                        <p className="text-xs text-muted-foreground">
                          <span className="font-medium">Out:</span> {g.output}
                        </p>
                      )}
                    </motion.div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Decision Graph */}
        <TabsContent value="decision" className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Decision Flow</CardTitle></CardHeader>
            <CardContent>
              {trace.execution_path.length === 0 ? (
                <p className="text-sm text-muted-foreground">No execution path data.</p>
              ) : (
                <div className="space-y-2">
                  {trace.execution_path.map((step, i) => {
                    const node = trace.graph_execution.find((g) => g.node_name === step.replace(/\(.*\)/, ""));
                    return (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="flex items-start gap-3"
                      >
                        <div className={cn(
                          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                          i === trace.execution_path.length - 1
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary text-secondary-foreground"
                        )}>
                          {i + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{step}</span>
                            {node && <LatencyBadge ms={node.execution_time_ms} />}
                          </div>
                          {node?.decision && (
                            <p className="text-xs text-muted-foreground mt-0.5">
                              Decision: {node.decision}
                              {node.next_node && <span> &rarr; {node.next_node}</span>}
                            </p>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Retrieval Inspector */}
        <TabsContent value="retrieval" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Retrieved Chunks ({trace.retrieval_details.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {trace.retrieval_details.length === 0 ? (
                <p className="text-sm text-muted-foreground">No retrieval data.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="px-2 py-2 text-left font-medium">Rank</th>
                        <th className="px-2 py-2 text-left font-medium">Chunk ID</th>
                        <th className="px-2 py-2 text-left font-medium">Vector Score</th>
                        <th className="px-2 py-2 text-left font-medium">BM25 Score</th>
                        <th className="px-2 py-2 text-left font-medium">Fusion Score</th>
                        <th className="px-2 py-2 text-left font-medium">Rerank Score</th>
                        <th className="px-2 py-2 text-left font-medium">Status</th>
                        <th className="px-2 py-2 text-left font-medium">Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trace.retrieval_details.map((r, i) => (
                        <tr key={i} className={cn("border-b border-border/50", r.selected ? "" : "opacity-50")}>
                          <td className="px-2 py-2">{r.final_rank}</td>
                          <td className="px-2 py-2 font-mono">{r.chunk_id.slice(0, 8)}...</td>
                          <td className="px-2 py-2">{r.vector_score.toFixed(4)}</td>
                          <td className="px-2 py-2">{r.bm25_score.toFixed(4)}</td>
                          <td className="px-2 py-2">{r.fusion_score.toFixed(4)}</td>
                          <td className="px-2 py-2">{r.rerank_score.toFixed(4)}</td>
                          <td className="px-2 py-2">
                            {r.selected
                              ? <span className="text-emerald-500 flex items-center gap-1"><CheckCircle className="h-3 w-3" />Selected</span>
                              : <span className="text-muted-foreground flex items-center gap-1"><XCircle className="h-3 w-3" />Rejected</span>
                            }
                          </td>
                          <td className="px-2 py-2 text-muted-foreground">{r.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Confidence Breakdown */}
        <TabsContent value="confidence" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">Confidence Breakdown</CardTitle></CardHeader>
              <CardContent>
                {trace.confidence_breakdown ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="text-3xl font-bold">{trace.confidence_breakdown.final_score.toFixed(1)}%</div>
                      <ConfidenceBadge level={trace.final_confidence_level as any} />
                    </div>
                    <Separator />
                    {[
                      { label: "Vector Similarity", value: trace.confidence_breakdown.vector_similarity, contrib: trace.confidence_breakdown.vector_contribution, pct: trace.confidence_breakdown.vector_contribution },
                      { label: "Cross Encoder Score", value: trace.confidence_breakdown.cross_encoder_score, contrib: trace.confidence_breakdown.cross_encoder_contribution, pct: trace.confidence_breakdown.cross_encoder_contribution },
                      { label: "Coverage", value: trace.confidence_breakdown.coverage, contrib: trace.confidence_breakdown.coverage_contribution, pct: trace.confidence_breakdown.coverage_contribution },
                    ].map((item) => (
                      <div key={item.label}>
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="text-muted-foreground">{item.label}</span>
                          <span className="font-medium">{item.contrib.toFixed(1)} pts</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${Math.min((item.contrib / (trace.confidence_breakdown!.final_score || 1)) * 100, 100)}%` }}
                              className="h-full rounded-full bg-primary"
                            />
                          </div>
                          <span className="text-xs text-muted-foreground w-10 text-right">
                            {item.value.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    ))}
                    <Separator />
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="rounded-lg bg-secondary/30 p-2">
                        <p className="text-xs text-muted-foreground">Citation Count</p>
                        <p className="font-medium">{trace.confidence_breakdown.citation_count}</p>
                      </div>
                      <div className="rounded-lg bg-secondary/30 p-2">
                        <p className="text-xs text-muted-foreground">Contradiction</p>
                        <p className="font-medium">{trace.confidence_breakdown.contradiction_status}</p>
                      </div>
                      <div className="rounded-lg bg-secondary/30 p-2">
                        <p className="text-xs text-muted-foreground">Retry Success</p>
                        <p className="font-medium">{trace.confidence_breakdown.retry_success ? "Yes" : "No"}</p>
                      </div>
                      <div className="rounded-lg bg-secondary/30 p-2">
                        <p className="text-xs text-muted-foreground">Raw Score</p>
                        <p className="font-medium">{trace.confidence_breakdown.raw_score.toFixed(4)}</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No confidence breakdown available.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-base">Contribution Distribution</CardTitle></CardHeader>
              <CardContent>
                {confidencePieData.length > 0 ? (
                  <div className="flex items-center justify-center">
                    <ResponsiveContainer width="100%" height={250}>
                      <RePieChart>
                        <Pie
                          data={confidencePieData}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={100}
                          dataKey="value"
                          label={(entry: any) => `${entry.name} ${((entry.percent ?? 0) * 100).toFixed(0)}%`}
                        >
                          {confidencePieData.map((_, i) => (
                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </RePieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No contribution data.</p>
                )}
              </CardContent>
            </Card>
          </div>

          {trace.llm_observability && (
            <Card>
              <CardHeader><CardTitle className="text-base">LLM Observability</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="rounded-lg bg-secondary/30 p-3">
                    <p className="text-xs text-muted-foreground">Model</p>
                    <p className="text-sm font-medium">{String(trace.llm_observability.model_name || "N/A")}</p>
                  </div>
                  <div className="rounded-lg bg-secondary/30 p-3">
                    <p className="text-xs text-muted-foreground">Temperature</p>
                    <p className="text-sm font-medium">{String(trace.llm_observability.temperature ?? "N/A")}</p>
                  </div>
                  <div className="rounded-lg bg-secondary/30 p-3">
                    <p className="text-xs text-muted-foreground">Retries</p>
                    <p className="text-sm font-medium">{trace.retrieval_attempts - 1}</p>
                  </div>
                  <div className="rounded-lg bg-secondary/30 p-3">
                    <p className="text-xs text-muted-foreground">Total Latency</p>
                    <p className="text-sm font-medium">{totalLatency.toFixed(0)}ms</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Latency */}
        <TabsContent value="latency" className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Latency Breakdown</CardTitle></CardHeader>
            <CardContent>
              {latencyData.length === 0 ? (
                <p className="text-sm text-muted-foreground">No latency data.</p>
              ) : (
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={latencyData} layout="vertical" margin={{ left: 100 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis type="number" unit="ms" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis type="category" dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={11} width={90} />
                      <Tooltip
                        contentStyle={{
                          background: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                        formatter={(value: any) => [`${value}ms`, "Latency"]}
                      />
                      <Bar dataKey="value" fill="hsl(142, 76%, 36%)" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Answer */}
        <TabsContent value="answer" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Generated Answer</CardTitle>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>Query: {trace.original_query}</span>
                {trace.rewritten_query && <span>&middot; Rewritten: {trace.rewritten_query}</span>}
              </div>
            </CardHeader>
            <CardContent>
              {trace.answer ? (
                <div className="rounded-lg bg-secondary/30 p-4 whitespace-pre-wrap text-sm leading-relaxed">
                  {trace.answer}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No answer generated.</p>
              )}

              {trace.citations.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium mb-2">Citations ({trace.citations.length})</h4>
                  <div className="space-y-2">
                    {trace.citations.map((cit, i) => (
                      <div key={i} className="rounded-lg border border-border p-3 text-xs">
                        <div className="flex items-center gap-2 text-muted-foreground mb-1">
                          <span className="font-medium">[{i + 1}]</span>
                          <span>Doc: {cit.document_id?.slice(0, 8)}...</span>
                          {cit.page != null && <span>Page {cit.page}</span>}
                        </div>
                        <p className="text-muted-foreground">{(cit.text || "").slice(0, 200)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Decision Summary</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div className="rounded-lg bg-secondary/30 p-2">
                  <p className="text-xs text-muted-foreground">Retrieval Attempts</p>
                  <p className="font-medium">{trace.retrieval_attempts}</p>
                </div>
                {trace.reason_for_retry && (
                  <div className="rounded-lg bg-secondary/30 p-2 col-span-2">
                    <p className="text-xs text-muted-foreground">Reason For Retry</p>
                    <p className="font-medium text-amber-500">{trace.reason_for_retry}</p>
                  </div>
                )}
                <div className="rounded-lg bg-secondary/30 p-2">
                  <p className="text-xs text-muted-foreground">Contradiction</p>
                  <p className={cn("font-medium", trace.contradiction_detected ? "text-red-500" : "text-emerald-500")}>
                    {trace.contradiction_detected ? "Detected" : "None"}
                  </p>
                </div>
                <div className="rounded-lg bg-secondary/30 p-2">
                  <p className="text-xs text-muted-foreground">Clarification</p>
                  <p className={cn("font-medium", trace.clarification_needed ? "text-amber-500" : "text-emerald-500")}>
                    {trace.clarification_needed ? "Needed" : "None"}
                  </p>
                </div>
                <div className="rounded-lg bg-secondary/30 p-2">
                  <p className="text-xs text-muted-foreground">Confidence Before</p>
                  <p className="font-medium">{trace.confidence_before_rewrite.toFixed(1)}%</p>
                </div>
                {trace.confidence_after_rewrite != null && (
                  <div className="rounded-lg bg-secondary/30 p-2">
                    <p className="text-xs text-muted-foreground">Confidence After</p>
                    <p className="font-medium">{trace.confidence_after_rewrite.toFixed(1)}%</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ExplainabilityContent() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const loadTraces = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchTraces();
      setTraces(data.traces);
    } catch (err) {
      console.error("Failed to load traces", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTraces();
  }, [loadTraces]);

  const handleSelectTrace = async (traceId: string) => {
    try {
      const trace = await fetchTrace(traceId);
      setSelectedTrace(trace);
    } catch (err) {
      console.error("Failed to load trace", err);
    }
  };

  const filteredTraces = traces.filter(
    (t) =>
      t.original_query.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (selectedTrace) {
    return <TraceDetail trace={selectedTrace} onBack={() => setSelectedTrace(null)} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">AI Explainability</h1>
          <p className="text-sm text-muted-foreground">Trace viewer, decision audit, and observability</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <a href={getExportUrl("json")} target="_blank" rel="noopener"><FileJson className="h-4 w-4 mr-1" />Export JSON</a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href={getExportUrl("csv")} target="_blank" rel="noopener"><Table className="h-4 w-4 mr-1" />Export CSV</a>
          </Button>
          <Button variant="outline" size="sm" onClick={loadTraces} disabled={loading}>
            <Eye className="h-4 w-4 mr-1" />Refresh
          </Button>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search traces by query or ID..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full rounded-lg border border-border bg-background pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      <div className="grid gap-3">
        {loading ? (
          <LoadingSkeleton />
        ) : filteredTraces.length === 0 ? (
          <EmptyState
            icon={GitBranch}
            title="No Traces Yet"
            description="Ask a question in the Chat panel to generate an execution trace."
          />
        ) : (
          <AnimatePresence>
            {filteredTraces.map((trace, i) => (
              <motion.div
                key={trace.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="cursor-pointer rounded-lg border border-border bg-card p-4 transition-all hover:border-primary/50 hover:shadow-sm"
                onClick={() => handleSelectTrace(trace.id)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium truncate">{trace.original_query}</span>
                      <ConfidenceBadge level={trace.final_confidence_level as any} score={trace.final_confidence} />
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>{new Date(trace.timestamp).toLocaleString()}</span>
                      <span>&middot;</span>
                      <span>{trace.retrieval_attempts} attempt{trace.retrieval_attempts !== 1 ? "s" : ""}</span>
                      <span>&middot;</span>
                      <span>{trace.execution_path.length} steps</span>
                      {trace.contradiction_detected && (
                        <>
                          <span>&middot;</span>
                          <span className="text-amber-500 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" />Contradiction
                          </span>
                        </>
                      )}
                      {trace.clarification_needed && (
                        <>
                          <span>&middot;</span>
                          <span className="text-amber-500 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" />Clarification
                          </span>
                        </>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 mt-2">
                      {trace.execution_path.slice(0, 6).map((step, j) => (
                        <Badge key={j} variant="secondary" className="text-[10px] px-1.5 py-0">
                          {step.replace(/\(.*\)/, "")}
                        </Badge>
                      ))}
                      {trace.execution_path.length > 6 && (
                        <span className="text-[10px] text-muted-foreground">+{trace.execution_path.length - 6}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-muted-foreground">{trace.id.slice(0, 8)}</span>
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
          <Download className="h-4 w-4 text-muted-foreground" />
          Export All Traces
        </h3>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <a href={getExportUrl("json")} target="_blank" rel="noopener"><FileJson className="h-4 w-4 mr-1" />Export as JSON</a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href={getExportUrl("csv")} target="_blank" rel="noopener"><Table className="h-4 w-4 mr-1" />Export as CSV</a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href={getExportUrl("markdown")} target="_blank" rel="noopener"><FileText className="h-4 w-4 mr-1" />Export as Markdown</a>
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function ExplainabilityPage() {
  return (
    <ErrorBoundary>
      <ExplainabilityContent />
    </ErrorBoundary>
  );
}
