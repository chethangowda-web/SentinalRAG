"use client";

import { useState } from "react";
import { Search, FileText, Loader2, Clock, Gauge, ArrowUpDown } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { useSearch } from "@/hooks/use-search";
import type { SearchResultItem } from "@/types";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const searchMutation = useSearch();
  const results = searchMutation.data?.results ?? [];
  const latencies = searchMutation.data?.latencies;

  const handleSearch = () => {
    if (!query.trim()) return;
    searchMutation.mutate({ query: query.trim() });
  };

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Search</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Search across all indexed documents with vector and BM25 hybrid retrieval.
          </p>
        </div>

        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Query"
              className="pl-9"
            />
          </div>
          <Button onClick={handleSearch} disabled={!query.trim() || searchMutation.isPending}>
            {searchMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
          </Button>
        </div>

        {searchMutation.isPending ? (
          <LoadingSkeleton type="card" count={3} />
        ) : searchMutation.data ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {results.length} retrieved chunks for &ldquo;{query}&rdquo;
              </p>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><Gauge className="h-3 w-3" /> Confidence: {Math.round(searchMutation.data.confidence * 100)}%</span>
                {latencies && (
                  <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {(Object.values(latencies).reduce((a, b) => a + b, 0) / 1000).toFixed(2)}s</span>
                )}
              </div>
            </div>

            {/* Results Table */}
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-secondary/50">
                    <th className="text-left p-3 font-medium text-xs text-muted-foreground">#</th>
                    <th className="text-left p-3 font-medium text-xs text-muted-foreground">Document</th>
                    <th className="text-left p-3 font-medium text-xs text-muted-foreground">Page</th>
                    <th className="text-left p-3 font-medium text-xs text-muted-foreground">Similarity</th>
                    <th className="text-left p-3 font-medium text-xs text-muted-foreground">BM25</th>
                    <th className="text-left p-3 font-medium text-xs text-muted-foreground">Rerank</th>
                    <th className="text-left p-3 font-medium text-xs text-muted-foreground">Chunk</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((item: SearchResultItem, i: number) => (
                    <tr key={item.chunk_id} className="border-b last:border-0 hover:bg-secondary/20 transition-colors">
                      <td className="p-3 text-xs text-muted-foreground">{i + 1}</td>
                      <td className="p-3">
                        <span className="text-xs font-medium">{item.filename || item.document_id.substring(0, 8)}</span>
                      </td>
                      <td className="p-3 text-xs text-muted-foreground">{item.page ?? "--"}</td>
                      <td className="p-3">
                        <Badge variant="outline" className="text-[10px]">
                          {(item.vector_score * 100).toFixed(1)}%
                        </Badge>
                      </td>
                      <td className="p-3">
                        <Badge variant="outline" className="text-[10px]">
                          {(item.bm25_score * 100).toFixed(1)}%
                        </Badge>
                      </td>
                      <td className="p-3">
                        <Badge variant={item.rerank_score > 0.5 ? "success" : "outline"} className="text-[10px]">
                          {item.rerank_score.toFixed(3)}
                        </Badge>
                      </td>
                      <td className="p-3">
                        <p className="text-xs text-muted-foreground line-clamp-2 max-w-[200px]">
                          {item.text}
                        </p>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Latency Breakdown */}
            {latencies && Object.keys(latencies).length > 0 && (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="h-4 w-4 text-primary" />
                    <span className="text-xs font-medium">Retrieval Latency</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {Object.entries(latencies).map(([key, val]) => (
                      <div key={key} className="rounded-lg bg-secondary/30 p-2.5 text-center">
                        <p className="text-xs font-bold">{val.toFixed(0)}ms</p>
                        <p className="text-[10px] text-muted-foreground capitalize">{key.replace(/_/g, " ")}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        ) : null}

        {!searchMutation.data && !searchMutation.isPending && (
          <EmptyState
            icon={Search}
            title="Search your documents"
            description="Enter a query above to search across all indexed content."
          />
        )}

        {searchMutation.error && (
          <Card className="border-destructive/20">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{searchMutation.error?.message || "Search failed."}</p>
            </CardContent>
          </Card>
        )}
      </div>
    </ErrorBoundary>
  );
}
