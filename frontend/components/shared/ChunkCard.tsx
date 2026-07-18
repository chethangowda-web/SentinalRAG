"use client";

import { FileText, BarChart3 } from "lucide-react";

interface ChunkCardProps {
  chunk: {
    document_id: string;
    text: string;
    rerank_score: number;
    page?: number | null;
    page_number?: number | null;
    filename?: string | null;
    section?: string | null;
  };
  index: number;
}

export function ChunkCard({ chunk, index }: ChunkCardProps) {
  const page = chunk.page ?? chunk.page_number;

  return (
    <div className="rounded-lg border border-border bg-card p-3 transition-colors hover:border-primary/30">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded bg-primary/10 text-[10px] font-bold text-primary">
            {index + 1}
          </span>
          <FileText className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-medium">{chunk.filename || chunk.document_id?.slice(0, 8)}</span>
        </div>
        <div className="flex items-center gap-2">
          {page != null && <span className="text-[10px] text-muted-foreground">p.{page}</span>}
          <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
            <BarChart3 className="h-3 w-3" />
            {chunk.rerank_score.toFixed(2)}
          </span>
        </div>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-muted-foreground line-clamp-3">
        {chunk.text}
      </p>
      {chunk.section && (
        <p className="mt-1 text-[10px] text-muted-foreground/60">Section: {chunk.section}</p>
      )}
    </div>
  );
}
