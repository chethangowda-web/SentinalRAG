"use client";

import type { CitationItem } from "@/types";
import { FileText, ExternalLink } from "lucide-react";

interface CitationCardProps {
  citation: CitationItem;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  return (
    <div className="group rounded-lg border border-border bg-secondary/50 p-3 transition-colors hover:border-primary/30">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded bg-primary/10 text-[10px] font-bold text-primary">
            {index + 1}
          </span>
          <FileText className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">{citation.document_id?.slice(0, 8)}...</span>
        </div>
        {citation.page && (
          <span className="text-[10px] text-muted-foreground">p.{citation.page}</span>
        )}
      </div>
      {citation.text && (
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground line-clamp-3">
          {citation.text}
        </p>
      )}
    </div>
  );
}
