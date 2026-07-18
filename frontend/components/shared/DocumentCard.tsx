"use client";

import type { Document } from "@/types";
import { FileText, Calendar, File } from "lucide-react";
import { StatusBadge } from "./StatusBadge";

interface DocumentCardProps {
  doc: Document;
  onClick?: () => void;
}

export function DocumentCard({ doc, onClick }: DocumentCardProps) {
  return (
    <div
      className="group cursor-pointer rounded-xl border border-border bg-card p-5 transition-all hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-primary/10 p-2.5">
            <File className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-sm font-medium leading-tight">{doc.filename}</p>
            <p className="text-xs text-muted-foreground">{doc.file_type?.toUpperCase()}</p>
          </div>
        </div>
        <StatusBadge status={doc.status} />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3 text-center text-xs">
        <div className="rounded-lg bg-secondary/50 p-2">
          <p className="font-medium text-foreground">{doc.pages ?? "-"}</p>
          <p className="text-muted-foreground">Pages</p>
        </div>
        <div className="rounded-lg bg-secondary/50 p-2">
          <p className="font-medium text-foreground">{doc.word_count ? (doc.word_count / 1000).toFixed(1) + "k" : "-"}</p>
          <p className="text-muted-foreground">Words</p>
        </div>
        <div className="rounded-lg bg-secondary/50 p-2">
          <p className="font-medium text-foreground">{doc.ocr_used ? "Yes" : "No"}</p>
          <p className="text-muted-foreground">OCR</p>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-1.5 text-[10px] text-muted-foreground">
        <Calendar className="h-3 w-3" />
        {new Date(doc.created_at).toLocaleDateString()}
      </div>
    </div>
  );
}
