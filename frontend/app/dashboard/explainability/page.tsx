"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Eye,
  Download,
  FileJson,
  FileText,
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
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RePieChart, Pie, Cell, Legend,
} from "recharts";
import { fetchTraces, fetchTrace, getExportUrl } from "@/services/traces";
import toast from "react-hot-toast";
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
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { Trace } from "@/types";

const confidenceColors: Record<string, string> = {
  HIGH: "#22c55e",
  MEDIUM: "#eab308",
  LOW: "#ef4444",
};

export default function ExplainabilityPage() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [tab, setTab] = useState("timeline");

  const loadTraces = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchTraces();
      setTraces(data.traces);
    } catch {
      toast.error("Failed to load traces");
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
    } catch {
      toast.error("Failed to load trace");
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
    <ErrorBoundary>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">AI Explainability</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Trace viewer, decision audit, and observability
            </p>
          </div>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search traces..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {loading ? (
          <LoadingSkeleton type="table" count={5} />
        ) : filteredTraces.length > 0 ? (
          <div className="space-y-2">
            <AnimatePresence>
              {filteredTraces.map((trace, i) => (
                <motion.div
                  key={trace.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                >
                  <Card
                    className="cursor-pointer transition-all duration-200 hover:shadow-md hover:border-primary/20"
                    onClick={() => handleSelectTrace(trace.id)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate">
                            {trace.original_query}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {new Date(trace.timestamp).toLocaleString()} · {trace.id.slice(0, 8)}...
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {trace.final_confidence_level && (
                            <ConfidenceBadge
                              level={trace.final_confidence_level}
                              score={trace.final_confidence}
                            />
                          )}
                          <Eye className="h-4 w-4 text-muted-foreground" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        ) : (
          <EmptyState
            icon={Search}
            title={searchQuery ? "No traces match your search" : "No traces yet"}
            description={
              searchQuery
                ? "Try a different search term."
                : "Traces appear when you ask questions in the Chat page."
            }
          />
        )}
      </div>
    </ErrorBoundary>
  );
}

function TraceDetail({ trace, onBack }: { trace: Trace; onBack: () => void }) {
  const [tab, setTab] = useState("timeline");

  const pieData = trace.confidence_breakdown
    ? [
        { name: "Vector", value: trace.confidence_breakdown.vector_similarity * 100 },
        { name: "Reranker", value: trace.confidence_breakdown.cross_encoder_score * 100 },
        { name: "Coverage", value: trace.confidence_breakdown.coverage * 100 },
      ]
    : [];

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="min-w-0 flex-1">
            <h1 className="text-lg font-bold tracking-tight truncate">{trace.original_query}</h1>
            <p className="text-xs text-muted-foreground">
              {new Date(trace.timestamp).toLocaleString()} · ID: {trace.id.slice(0, 8)}...
            </p>
          </div>
        </div>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full justify-start overflow-x-auto">
            <TabsTrigger value="timeline">
              <GitBranch className="mr-2 h-4 w-4" />
              Timeline
            </TabsTrigger>
            <TabsTrigger value="confidence">
              <PieChart className="mr-2 h-4 w-4" />
              Confidence
            </TabsTrigger>
            <TabsTrigger value="retrieval">
              <Layers className="mr-2 h-4 w-4" />
              Retrieval
            </TabsTrigger>
            <TabsTrigger value="latency">
              <Clock className="mr-2 h-4 w-4" />
              Latency
            </TabsTrigger>
          </TabsList>

          <TabsContent value="timeline" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Execution Path</CardTitle>
              </CardHeader>
              <CardContent>
                {trace.execution_path && trace.execution_path.length > 0 ? (
                  <div className="space-y-2">
                    {trace.execution_path.map((step, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                          <span className="text-xs font-medium text-primary">{i + 1}</span>
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium capitalize">{step.replace(/_/g, " ")}</p>
                        </div>
                        {trace.graph_execution?.[i] && (
                          <span className="text-xs text-muted-foreground">
                            {trace.graph_execution[i].execution_time_ms?.toFixed(0)}ms
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                    <GitBranch className="h-4 w-4" />
                    {trace.reasoning_path?.join(" → ") || "No execution path data"}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="confidence" className="mt-4">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Score Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  {trace.confidence_breakdown ? (
                    <div className="space-y-3">
                      <BreakdownRow
                        label="Vector Similarity (30%)"
                        value={trace.confidence_breakdown.vector_similarity}
                      />
                      <BreakdownRow
                        label="Cross-Encoder (50%)"
                        value={trace.confidence_breakdown.cross_encoder_score}
                      />
                      <BreakdownRow
                        label="Coverage (20%)"
                        value={trace.confidence_breakdown.coverage}
                      />
                      <Separator />
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Final Score</span>
                        <ConfidenceBadge
                          level={trace.final_confidence_level!}
                          score={trace.final_confidence}
                        />
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground py-4">No confidence data available</p>
                  )}
                </CardContent>
              </Card>

              {pieData.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Distribution</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={250}>
                      <RePieChart>
                        <Pie
                          data={pieData}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={90}
                          paddingAngle={2}
                          dataKey="value"
                        >
                          {pieData.map((entry, i) => (
                            <Cell key={i} fill={[hsl(221, 83, 53), hsl(142, 76, 36), hsl(38, 92, 50)][i]} />
                          ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                      </RePieChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          <TabsContent value="retrieval" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Retrieved Chunks</CardTitle>
              </CardHeader>
              <CardContent>
                {trace.retrieval_details && trace.retrieval_details.length > 0 ? (
                  <ScrollArea className="h-[400px]">
                    <div className="space-y-3">
                      {trace.retrieval_details.map((detail, i) => (
                        <Card key={i} className="bg-secondary/30">
                          <CardContent className="p-3">
                            <div className="flex items-start gap-3">
                              <span className="text-xs font-mono text-muted-foreground shrink-0 mt-0.5">
                                #{i + 1}
                              </span>
                              <div className="min-w-0">
                                <p className="text-sm line-clamp-3">{detail.text}</p>
                                <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                                  <span>Vector: {(detail.vector_score * 100).toFixed(0)}%</span>
                                  <span>BM25: {(detail.bm25_score * 100).toFixed(0)}%</span>
                                  <span>Rerank: {detail.rerank_score?.toFixed(2)}</span>
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </ScrollArea>
                ) : (
                  <p className="text-sm text-muted-foreground py-4">No retrieval data available</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="latency" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Latency Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                {trace.latencies && typeof trace.latencies === "object" && Object.keys(trace.latencies).length > 0 ? (
                  <div className="space-y-2">
                    {Object.entries(trace.latencies).map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-secondary/30 transition-colors">
                        <span className="text-sm capitalize">{key.replace(/_/g, " ")}</span>
                        <LatencyBadge ms={typeof val === "number" ? val : 0} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-4">No latency data available</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </ErrorBoundary>
  );
}

function BreakdownRow({ label, value }: { label: string; value?: number }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm">{label}</span>
      <span className={`text-sm font-medium ${value !== undefined ? (value >= 0.7 ? "text-success" : value >= 0.4 ? "text-warning" : "text-destructive") : ""}`}>
        {value !== undefined ? `${(value * 100).toFixed(0)}%` : "--"}
      </span>
    </div>
  );
}

function hsl(h: number, s: number, l: number) {
  return `hsl(${h}, ${s}%, ${l}%)`;
}
