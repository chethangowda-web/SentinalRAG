"use client";

import { useState } from "react";
import { Search, FileText, Loader2 } from "lucide-react";
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
            Search across all your documents.
          </p>
        </div>

        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search documents, chunks, and content..."
              className="pl-9"
            />
          </div>
          <Button onClick={handleSearch} disabled={!query.trim() || searchMutation.isPending}>
            {searchMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Search"
            )}
          </Button>
        </div>

        {searchMutation.isPending ? (
          <LoadingSkeleton type="card" count={3} />
        ) : searchMutation.data ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Found {results.length} result{results.length !== 1 ? "s" : ""} for &ldquo;{query}&rdquo;
              {searchMutation.data.confidence !== undefined && (
                <span className="ml-2">
                  · Confidence: {searchMutation.data.confidence_level} ({Math.round(searchMutation.data.confidence)})
                </span>
              )}
            </p>
            <div className="space-y-3">
              {results.map((item: SearchResultItem, i: number) => (
                <Card key={item.chunk_id}>
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        <FileText className="h-4 w-4 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium">{item.filename}</span>
                          {item.page && (
                            <span className="text-xs text-muted-foreground">Page {item.page}</span>
                          )}
                          {item.section && (
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                              {item.section}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-4">
                          {item.text}
                        </p>
                        <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                          <span>Vector: {(item.vector_score * 100).toFixed(1)}%</span>
                          <span>BM25: {(item.bm25_score * 100).toFixed(1)}%</span>
                          {item.rerank_score !== undefined && (
                            <span>Rerank: {item.rerank_score.toFixed(2)}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
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
              <p className="text-sm text-destructive">
                {searchMutation.error?.message || "Search failed. Please try again."}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </ErrorBoundary>
  );
}
