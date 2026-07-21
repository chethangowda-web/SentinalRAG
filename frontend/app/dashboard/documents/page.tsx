"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, FileText, Calendar, Layers, Trash2, RefreshCw, ArrowUpDown } from "lucide-react";
import toast from "react-hot-toast";
import { useDocuments, useDocumentChunks, useDeleteDocument } from "@/hooks/use-documents";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { Document as DocType } from "@/types";

function DocumentsContent() {
  const { data: documents, isLoading, error, refetch } = useDocuments();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"date" | "name">("date");
  const [selectedDoc, setSelectedDoc] = useState<DocType | null>(null);
  const { data: chunkData } = useDocumentChunks(selectedDoc?.id || null);
  const deleteDoc = useDeleteDocument();

  const filtered = useMemo(() => {
    if (!documents) return [];
    let list = documents.filter((d) =>
      d.filename.toLowerCase().includes(search.toLowerCase())
    );
    if (sortBy === "date") {
      list = [...list].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    } else {
      list = [...list].sort((a, b) => a.filename.localeCompare(b.filename));
    }
    return list;
  }, [documents, search, sortBy]);

  const handleDelete = async (e: React.MouseEvent, doc: DocType) => {
    e.stopPropagation();
    if (confirm(`Delete "${doc.filename}"? This cannot be undone.`)) {
      await deleteDoc.mutateAsync(doc.id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Documents</h1>
          <p className="text-sm text-muted-foreground">Manage your uploaded documents</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search documents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Button variant="outline" size="icon" onClick={() => refetch()} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setSortBy(sortBy === "date" ? "name" : "date")}>
            <ArrowUpDown className="mr-1 h-3 w-3" />
            {sortBy === "date" ? "Date" : "Name"}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <LoadingSkeleton type="card" count={4} />
      ) : error ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Failed to load documents. Please check the backend connection.
          </CardContent>
        </Card>
      ) : filtered && filtered.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence>
            {filtered.map((doc) => (
              <motion.div
                key={doc.id}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="group cursor-pointer rounded-xl border border-border bg-card p-5 transition-all hover:border-primary/30 hover:shadow-lg"
                onClick={() => setSelectedDoc(doc)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-primary/10 p-2.5">
                      <FileText className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{doc.filename}</p>
                      <p className="text-xs text-muted-foreground">{doc.file_type?.toUpperCase()}</p>
                    </div>
                  </div>
                  <StatusBadge status={doc.status} />
                </div>

                <div className="mt-4 grid grid-cols-3 gap-1 sm:gap-2 text-center text-xs">
                  <div className="rounded-lg bg-secondary/50 p-2">
                    <p className="font-medium text-foreground">{doc.pages ?? "-"}</p>
                    <p className="text-muted-foreground">Pages</p>
                  </div>
                  <div className="rounded-lg bg-secondary/50 p-2">
                    <p className="font-medium text-foreground">
                      {doc.word_count ? (doc.word_count / 1000).toFixed(1) + "k" : "-"}
                    </p>
                    <p className="text-muted-foreground">Words</p>
                  </div>
                  <div className="rounded-lg bg-secondary/50 p-2">
                    <p className="font-medium text-foreground">{doc.ocr_used ? "Yes" : "No"}</p>
                    <p className="text-muted-foreground">OCR</p>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    {new Date(doc.created_at).toLocaleDateString()}
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, doc)}
                    className="rounded p-1 text-muted-foreground opacity-0 transition-all hover:bg-red-500/10 hover:text-red-500 group-hover:opacity-100"
                    title="Delete document"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      ) : (
        <EmptyState
          icon={FileText}
          title="No documents found"
          description={search ? "No documents match your search." : "Upload your first document to get started."}
        />
      )}

      <Dialog open={!!selectedDoc} onOpenChange={(open) => { if (!open) setSelectedDoc(null); }}>
        {selectedDoc && (
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                {selectedDoc.filename}
              </DialogTitle>
              <DialogDescription>
                Document details and chunks
              </DialogDescription>
            </DialogHeader>

            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                { label: "Status", value: <StatusBadge status={selectedDoc.status} /> },
                { label: "Type", value: selectedDoc.file_type?.toUpperCase() },
                { label: "Pages", value: selectedDoc.pages ?? "-" },
                { label: "Words", value: selectedDoc.word_count?.toLocaleString() ?? "-" },
                { label: "OCR", value: selectedDoc.ocr_used ? "Yes" : "No" },
                { label: "Created", value: new Date(selectedDoc.created_at).toLocaleString() },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-lg bg-secondary/50 p-3">
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <div className="mt-1 font-medium">{value}</div>
                </div>
              ))}
            </div>

            <Separator />

            <div>
              <div className="mb-2 flex items-center gap-2">
                <Layers className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm font-medium">Chunks ({chunkData?.total_chunks || 0})</p>
              </div>
              <ScrollArea className="h-64">
                <div className="space-y-2">
                  {chunkData?.chunks?.map((chunk) => (
                    <div key={chunk.id} className="rounded-lg border border-border p-3">
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>Chunk #{chunk.chunk_index}</span>
                        <div className="flex items-center gap-2">
                          {chunk.page_number && <span>p.{chunk.page_number}</span>}
                          <StatusBadge status={chunk.embedding_status} />
                        </div>
                      </div>
                      <p className="mt-1 text-xs leading-relaxed text-foreground/80 line-clamp-2">
                        {chunk.chunk_text}
                      </p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <ErrorBoundary>
      <DocumentsContent />
    </ErrorBoundary>
  );
}
