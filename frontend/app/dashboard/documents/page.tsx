"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDocuments, useDocumentChunks, useDeleteDocument } from "@/hooks/use-documents";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import toast from "react-hot-toast";
import {
  FileText,
  Search,
  Trash2,
  Calendar,
  File,
  BarChart3,
  BookOpen,
  ArrowUpDown,
  X,
} from "lucide-react";
import type { Document } from "@/types";

type SortBy = "date" | "name" | "status";

export default function DocumentsPage() {
  const { data: documents, isLoading } = useDocuments();
  const deleteDoc = useDeleteDocument();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<SortBy>("date");
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const { data: chunks } = useDocumentChunks(selectedDoc?.id ?? null);

  const filtered = (documents ?? [])
    .filter(
      (doc) =>
        doc.filename.toLowerCase().includes(search.toLowerCase()) ||
        doc.status.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === "name") return a.filename.localeCompare(b.filename);
      if (sortBy === "status") return a.status.localeCompare(b.status);
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  const handleDelete = async (id: string, filename: string) => {
    try {
      await deleteDoc.mutateAsync(id);
      toast.success(`Deleted "${filename}"`);
    } catch {
      toast.error("Failed to delete document");
    }
  };

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Documents</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Manage your uploaded documents
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search documents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex items-center gap-2">
            {(["date", "name", "status"] as const).map((s) => (
              <Button
                key={s}
                variant={sortBy === s ? "default" : "outline"}
                size="sm"
                onClick={() => setSortBy(s)}
              >
                {s === "date" && <Calendar className="mr-1.5 h-3.5 w-3.5" />}
                {s === "name" && <FileText className="mr-1.5 h-3.5 w-3.5" />}
                {s === "status" && <BarChart3 className="mr-1.5 h-3.5 w-3.5" />}
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <LoadingSkeleton type="table" count={5} />
        ) : filtered.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <AnimatePresence>
              {filtered.map((doc, i) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <Card
                    className="cursor-pointer transition-all duration-200 hover:shadow-md hover:border-primary/20"
                    onClick={() => setSelectedDoc(doc)}
                  >
                    <CardContent className="p-5">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            <FileText className="h-5 w-5 text-primary" />
                          </div>
                          <div>
                            <p className="text-sm font-medium leading-tight">{doc.filename}</p>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {doc.word_count?.toLocaleString() ?? 0} words
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="shrink-0 -mr-2 -mt-1"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(doc.id, doc.filename);
                          }}
                        >
                          <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                        </Button>
                      </div>

                      <Separator className="my-3" />

                      <div className="flex items-center justify-between">
                        <StatusBadge status={doc.status} />
                        <span className="text-xs text-muted-foreground">
                          {new Date(doc.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        ) : (
          <EmptyState
            icon={FileText}
            title={search ? "No documents match your search" : "No documents yet"}
            description={
              search
                ? "Try a different search term."
                : "Upload your first document to get started with RAG."
            }
          />
        )}

        <Dialog open={!!selectedDoc} onOpenChange={() => setSelectedDoc(null)}>
          <DialogContent className="max-w-2xl max-h-[80vh]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                {selectedDoc?.filename}
              </DialogTitle>
              <DialogDescription>
                {selectedDoc?.word_count?.toLocaleString() ?? 0} words ·{" "}
                {selectedDoc?.pages ?? "--"} pages
                {selectedDoc?.ocr_used ? " · OCR applied" : ""}
              </DialogDescription>
            </DialogHeader>

            <Separator />

            <div className="flex items-center gap-2">
              <StatusBadge status={selectedDoc?.status ?? ""} />
              <span className="text-xs text-muted-foreground ml-auto">
                Created {selectedDoc?.created_at ? new Date(selectedDoc.created_at).toLocaleString() : ""}
              </span>
            </div>

            <Separator />

            <div className="space-y-2">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-muted-foreground" />
                Chunks ({chunks?.chunks?.length ?? 0})
              </h4>
              <ScrollArea className="h-[300px]">
                <div className="space-y-2">
                  {chunks?.chunks?.map((chunk, i) => (
                    <Card key={chunk.id} className="bg-secondary/30">
                      <CardContent className="p-3">
                        <div className="flex items-start gap-3">
                          <span className="text-xs font-mono text-muted-foreground shrink-0 mt-0.5">
                            #{i + 1}
                          </span>
                          <div className="min-w-0">
                            <p className="text-xs text-muted-foreground line-clamp-3">
                              {chunk.chunk_text}
                            </p>
                            {chunk.page_number && (
                              <p className="text-xs text-muted-foreground mt-1">
                                Page {chunk.page_number}
                              </p>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                  {(!chunks?.chunks || chunks.chunks.length === 0) && (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No chunks available
                    </p>
                  )}
                </div>
              </ScrollArea>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </ErrorBoundary>
  );
}
