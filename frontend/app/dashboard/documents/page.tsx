"use client";

import { useState, useMemo } from "react";
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
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import toast from "react-hot-toast";
import {
  FileText,
  Search,
  Trash2,
  Calendar,
  BarChart3,
  Eye,
  Database,
  Scan,
  Brain,
  Hash,
  File,
  Clock,
  Layers,
  BookOpen,
  AlertTriangle,
  CheckCircle2,
  Filter,
  MessageSquare,
  Upload,
  HardDrive,
  SortAsc,
  Gauge,
  Shield,
  Zap,
  Sparkles,
  MoreHorizontal,
  ExternalLink,
  X,
} from "lucide-react";
import Link from "next/link";
import type { Document } from "@/types";

type SortBy = "date" | "name" | "status" | "confidence";

function OcrBadge({ quality }: { quality?: string | null }) {
  const colorMap: Record<string, string> = {
    excellent: "text-success border-success/30 bg-success/10",
    good: "text-primary border-primary/30 bg-primary/10",
    fair: "text-warning border-warning/30 bg-warning/10",
    poor: "text-destructive border-destructive/30 bg-destructive/10",
    very_poor: "text-destructive border-destructive/30 bg-destructive/10",
  };
  if (!quality) return null;
  return (
    <Badge variant="outline" className={`text-[10px] ${colorMap[quality] ?? ""}`}>
      <Scan className="h-3 w-3 mr-1" />
      {quality.replace(/_/g, " ")}
    </Badge>
  );
}

function ConfidenceScore({ score }: { score?: number | null }) {
  if (score == null) return null;
  const pct = Math.min(Math.max(score * 100, 0), 100);
  const color = pct >= 80 ? "hsl(var(--success))" : pct >= 50 ? "hsl(var(--warning))" : "hsl(var(--destructive))";
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-16 rounded-full bg-secondary overflow-hidden">
              <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
            </div>
            <span className="text-[10px] font-medium tabular-nums" style={{ color }}>{pct.toFixed(0)}%</span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p className="text-[10px]">OCR Confidence Score</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function ProcessingStatus({ status }: { status: string }) {
  const config: Record<string, { label: string; color: string; bg: string }> = {
    completed: { label: "Completed", color: "text-success", bg: "bg-success/10" },
    embedded: { label: "Embedded", color: "text-success", bg: "bg-success/10" },
    processing: { label: "Processing", color: "text-warning", bg: "bg-warning/10" },
    pending: { label: "Pending", color: "text-muted-foreground", bg: "bg-muted" },
    failed: { label: "Failed", color: "text-destructive", bg: "bg-destructive/10" },
    uploaded: { label: "Uploaded", color: "text-primary", bg: "bg-primary/10" },
  };
  const c = config[status.toLowerCase()] ?? { label: status, color: "text-muted-foreground", bg: "bg-muted" };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${c.color} ${c.bg}`}>
      {status.toLowerCase() === "processing" && <span className="h-1.5 w-1.5 rounded-full bg-warning animate-pulse-soft" />}
      {status.toLowerCase() === "completed" && <CheckCircle2 className="h-3 w-3" />}
      {status.toLowerCase() === "failed" && <X className="h-3 w-3" />}
      {c.label}
    </span>
  );
}

function formatFileSize(bytes?: number | null): string {
  if (bytes == null) return "--";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentsPage() {
  const { data: documents, isLoading } = useDocuments();
  const deleteDoc = useDeleteDocument();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<SortBy>("date");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterOcr, setFilterOcr] = useState<string>("all");
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const { data: chunks } = useDocumentChunks(selectedDoc?.id ?? null);

  const statusOptions = ["all", "completed", "embedded", "processing", "pending", "failed", "uploaded"];
  const ocrOptions = ["all", "excellent", "good", "fair", "poor", "very_poor"];

  const filtered = useMemo(() => {
    return (documents ?? [])
      .filter((doc) => {
        if (filterStatus !== "all" && doc.status !== filterStatus) return false;
        if (filterOcr !== "all" && doc.ocr_quality !== filterOcr) return false;
        return (
          doc.filename.toLowerCase().includes(search.toLowerCase()) ||
          doc.status.toLowerCase().includes(search.toLowerCase()) ||
          (doc.document_type ?? "").toLowerCase().includes(search.toLowerCase())
        );
      })
      .sort((a, b) => {
        if (sortBy === "name") return a.filename.localeCompare(b.filename);
        if (sortBy === "status") return a.status.localeCompare(b.status);
        if (sortBy === "confidence") return ((b.ocr_confidence ?? 0) - (a.ocr_confidence ?? 0));
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
  }, [documents, search, sortBy, filterStatus, filterOcr]);

  const handleDelete = async (id: string, filename: string) => {
    try {
      await deleteDoc.mutateAsync(id);
      toast.success(`Deleted "${filename}"`);
    } catch {
      toast.error("Failed to delete document");
    }
  };

  const getEvalRoute = (doc: Document) => {
    return `/dashboard/evaluation`;
  };

  const getChatRoute = (doc: Document) => {
    return `/dashboard/chat`;
  };

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Documents</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Manage your uploaded and indexed documents
            </p>
          </div>
          <Link href="/dashboard/upload">
            <Button>
              <Upload className="mr-2 h-4 w-4" />
              Upload Document
            </Button>
          </Link>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search documents by name, status, or type..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-9 text-sm"
            />
          </div>
          <div className="flex items-center gap-2">
            <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortBy)}>
              <SelectTrigger className="h-9 w-36 text-xs">
                <SortAsc className="h-3.5 w-3.5 mr-2" />
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="date">Date</SelectItem>
                <SelectItem value="name">Name</SelectItem>
                <SelectItem value="status">Status</SelectItem>
                <SelectItem value="confidence">Confidence</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="h-9 w-36 text-xs">
                <Filter className="h-3.5 w-3.5 mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map((s) => (
                  <SelectItem key={s} value={s}>{s === "all" ? "All Status" : s.charAt(0).toUpperCase() + s.slice(1)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterOcr} onValueChange={setFilterOcr}>
              <SelectTrigger className="h-9 w-36 text-xs">
                <Scan className="h-3.5 w-3.5 mr-2" />
                <SelectValue placeholder="OCR Quality" />
              </SelectTrigger>
              <SelectContent>
                {ocrOptions.map((o) => (
                  <SelectItem key={o} value={o}>{o === "all" ? "All Quality" : o.replace(/_/g, " ")}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="rounded-xl border bg-card overflow-hidden">
                <div className="p-5 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-muted animate-pulse" />
                    <div className="space-y-2 flex-1">
                      <div className="h-4 w-32 bg-muted rounded animate-pulse" />
                      <div className="h-3 w-20 bg-muted rounded animate-pulse" />
                    </div>
                  </div>
                  <div className="h-px bg-border" />
                  <div className="grid grid-cols-2 gap-2">
                    <div className="h-3 w-16 bg-muted rounded animate-pulse" />
                    <div className="h-3 w-16 bg-muted rounded animate-pulse" />
                    <div className="h-3 w-16 bg-muted rounded animate-pulse" />
                    <div className="h-3 w-16 bg-muted rounded animate-pulse" />
                  </div>
                  <div className="h-px bg-border" />
                  <div className="flex justify-between">
                    <div className="h-5 w-20 bg-muted rounded-full animate-pulse" />
                    <div className="h-3 w-16 bg-muted rounded animate-pulse" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <AnimatePresence>
              {filtered.map((doc, i) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03, duration: 0.3 }}
                  layout
                >
                  <Card className="group overflow-hidden transition-all duration-200 hover:shadow-md hover:border-primary/20 h-full">
                    <CardContent className="p-0">
                      <div className="p-5">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 group-hover:bg-primary/15 transition-colors">
                              <File className="h-5 w-5 text-primary" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium leading-tight truncate group-hover:text-primary transition-colors">{doc.filename}</p>
                              <p className="text-[10px] text-muted-foreground mt-0.5">
                                {doc.file_type?.toUpperCase() || "PDF"} · {formatFileSize(doc.file_size)}
                              </p>
                            </div>
                          </div>
                        </div>

                        <Separator className="my-3" />

                        <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-xs">
                          <div className="flex items-center gap-1.5 text-muted-foreground">
                            <Calendar className="h-3 w-3 shrink-0" />
                            <span className="truncate">{new Date(doc.created_at).toLocaleDateString()}</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-muted-foreground">
                            <FileText className="h-3 w-3 shrink-0" />
                            <span>{doc.pages ?? "--"} pages</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-muted-foreground">
                            <Layers className="h-3 w-3 shrink-0" />
                            <span>{doc.chunk_count ?? "--"} chunks</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-muted-foreground">
                            <Clock className="h-3 w-3 shrink-0" />
                            <span>{doc.estimated_reading_time ? `${doc.estimated_reading_time}m read` : "--"}</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 mt-3 flex-wrap">
                          <ProcessingStatus status={doc.status} />
                          <OcrBadge quality={doc.ocr_quality} />
                          {doc.document_type && doc.document_type !== "unknown" && doc.document_type !== "other" && (
                            <Badge variant="secondary" className="text-[10px] capitalize">
                              <BookOpen className="h-3 w-3 mr-1" />
                              {doc.document_type.replace(/_/g, " ")}
                            </Badge>
                          )}
                        </div>

                        <Separator className="my-3" />

                        <div className="flex items-center justify-between">
                          <ConfidenceScore score={doc.ocr_confidence} />
                          <span className="text-[10px] text-muted-foreground">
                            ID: {doc.id.slice(0, 8)}...
                          </span>
                        </div>
                      </div>

                      <div className="border-t bg-muted/30 px-4 py-2 flex items-center justify-between gap-1">
                        <div className="flex items-center gap-1">
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setSelectedDoc(doc)}>
                                  <Eye className="h-3.5 w-3.5" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Preview</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Link href={getChatRoute(doc)}>
                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                                    <MessageSquare className="h-3.5 w-3.5" />
                                  </Button>
                                </Link>
                              </TooltipTrigger>
                              <TooltipContent>Open Chat</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Link href={getEvalRoute(doc)}>
                                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                                    <BarChart3 className="h-3.5 w-3.5" />
                                  </Button>
                                </Link>
                              </TooltipTrigger>
                              <TooltipContent>Evaluation</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                                onClick={(e) => { e.stopPropagation(); handleDelete(doc.id, doc.filename); }}
                                disabled={deleteDoc.isPending}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Delete</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        ) : (
          <EmptyState
            icon={search || filterStatus !== "all" || filterOcr !== "all" ? Search : FileText}
            title={search || filterStatus !== "all" || filterOcr !== "all" ? "No documents match your filters" : "No documents yet"}
            description={search || filterStatus !== "all" || filterOcr !== "all" ? "Try adjusting your search or filter criteria." : "Upload your first document to get started with the RAG pipeline."}
            action={!search && filterStatus === "all" && filterOcr === "all" ? (
              <Link href="/dashboard/upload">
                <Button>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Document
                </Button>
              </Link>
            ) : undefined}
          />
        )}

        <Dialog open={!!selectedDoc} onOpenChange={() => setSelectedDoc(null)}>
          <DialogContent className="max-w-2xl max-h-[85vh]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <File className="h-5 w-5 text-primary" />
                {selectedDoc?.filename}
              </DialogTitle>
              <DialogDescription>
                {selectedDoc?.file_type?.toUpperCase() || "PDF"} · {selectedDoc?.pages ?? "--"} pages · {selectedDoc?.word_count?.toLocaleString() ?? 0} words
                {selectedDoc?.estimated_reading_time ? ` · ${selectedDoc.estimated_reading_time} min read` : ""}
              </DialogDescription>
            </DialogHeader>

            <div className="flex items-center gap-2 mb-4">
              <StatusBadge status={selectedDoc?.status ?? ""} />
              <OcrBadge quality={selectedDoc?.ocr_quality} />
              {selectedDoc?.document_type && selectedDoc.document_type !== "unknown" && (
                <Badge variant="secondary" className="text-[10px] capitalize">{selectedDoc.document_type.replace(/_/g, " ")}</Badge>
              )}
            </div>

            <Tabs defaultValue="summary">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="summary">Summary</TabsTrigger>
                <TabsTrigger value="chunks">Chunks</TabsTrigger>
                <TabsTrigger value="metadata">Metadata</TabsTrigger>
                <TabsTrigger value="preview">Preview</TabsTrigger>
              </TabsList>

              <TabsContent value="summary" className="mt-4">
                {selectedDoc?.summary ? (
                  <div className="space-y-4">
                    <div className="rounded-xl bg-secondary/30 p-4">
                      <p className="text-sm leading-relaxed">{selectedDoc.summary}</p>
                    </div>
                    {selectedDoc.key_topics && selectedDoc.key_topics.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">Key Topics</p>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedDoc.key_topics.map((topic) => (
                            <Badge key={topic} variant="secondary" className="text-xs">{topic}</Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    {selectedDoc.keywords && selectedDoc.keywords.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">Keywords</p>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedDoc.keywords.map((kw) => (
                            <Badge key={kw} variant="outline" className="text-xs">{kw}</Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-8 text-center">No summary available for this document.</p>
                )}
              </TabsContent>

              <TabsContent value="chunks" className="mt-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-medium text-muted-foreground">{chunks?.chunks?.length ?? 0} chunks</span>
                  <ProcessingStatus status={selectedDoc?.status ?? ""} />
                </div>
                <ScrollArea className="h-[300px]">
                  <div className="space-y-2">
                    {chunks?.chunks?.map((chunk, i) => (
                      <Card key={chunk.id} className="bg-secondary/30 border-border/50">
                        <CardContent className="p-3">
                          <div className="flex items-start gap-3">
                            <span className="text-xs font-mono text-muted-foreground shrink-0 mt-0.5">#{i + 1}</span>
                            <div className="min-w-0 flex-1">
                              <p className="text-xs text-muted-foreground line-clamp-3">{chunk.chunk_text}</p>
                              <div className="flex items-center gap-2 mt-1.5">
                                {chunk.page_number && <Badge variant="outline" className="text-[10px]">Page {chunk.page_number}</Badge>}
                                <Badge variant="outline" className="text-[10px]">{chunk.word_count ?? 0} words</Badge>
                                <Badge variant={chunk.embedding_status === "embedded" ? "success" : "outline"} className="text-[10px]">{chunk.embedding_status}</Badge>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                    {(!chunks?.chunks || chunks.chunks.length === 0) && (
                      <p className="text-sm text-muted-foreground text-center py-8">No chunks available for this document.</p>
                    )}
                  </div>
                </ScrollArea>
              </TabsContent>

              <TabsContent value="metadata" className="mt-4">
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <MetaField label="File Type" value={selectedDoc?.file_type?.toUpperCase() || "PDF"} />
                    <MetaField label="File Size" value={formatFileSize(selectedDoc?.file_size)} />
                    <MetaField label="Pages" value={selectedDoc?.pages?.toString() ?? "--"} />
                    <MetaField label="Words" value={selectedDoc?.word_count?.toLocaleString() ?? "0"} />
                    <MetaField label="Characters" value={selectedDoc?.char_count?.toLocaleString() ?? "0"} />
                    <MetaField label="Reading Time" value={selectedDoc?.estimated_reading_time ? `${selectedDoc.estimated_reading_time} min` : "--"} />
                    <MetaField label="OCR Used" value={selectedDoc?.ocr_used ? "Applied" : "Not Required"} />
                    <MetaField label="OCR Quality" value={selectedDoc?.ocr_quality?.replace(/_/g, " ") ?? "--"} />
                    <MetaField label="OCR Confidence" value={selectedDoc?.ocr_confidence != null ? `${(selectedDoc.ocr_confidence * 100).toFixed(1)}%` : "--"} />
                    <MetaField label="Document Type" value={selectedDoc?.document_type?.replace(/_/g, " ") ?? "--"} />
                    <MetaField label="Chunks" value={selectedDoc?.chunk_count?.toString() ?? "--"} />
                    <MetaField label="Status" value={selectedDoc?.status ?? "--"} />
                  </div>
                  <Separator />
                  <div className="grid grid-cols-2 gap-3">
                    <MetaField label="Created" value={selectedDoc?.created_at ? new Date(selectedDoc.created_at).toLocaleString() : "--"} />
                    <MetaField label="Last Updated" value={selectedDoc?.updated_at ? new Date(selectedDoc.updated_at).toLocaleString() : "--"} />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="preview" className="mt-4">
                <ScrollArea className="h-[300px]">
                  <div className="space-y-2">
                    {chunks?.chunks?.slice(0, 5).map((chunk, i) => (
                      <div key={chunk.id} className="rounded-lg border p-3">
                        <p className="text-xs text-muted-foreground leading-relaxed">{chunk.chunk_text}</p>
                        {chunk.page_number && (
                          <p className="text-xs text-muted-foreground mt-1">— Page {chunk.page_number}</p>
                        )}
                      </div>
                    ))}
                    {(!chunks?.chunks || chunks.chunks.length === 0) && (
                      <p className="text-sm text-muted-foreground text-center py-8">No preview available.</p>
                    )}
                  </div>
                </ScrollArea>
              </TabsContent>
            </Tabs>

            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <div className="flex items-center gap-2">
                <Link href={`/dashboard/chat`}>
                  <Button variant="outline" size="sm">
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Open Chat
                  </Button>
                </Link>
                <Link href={`/dashboard/evaluation`}>
                  <Button variant="outline" size="sm">
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Evaluation
                  </Button>
                </Link>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive"
                onClick={() => { if (selectedDoc) handleDelete(selectedDoc.id, selectedDoc.filename); setSelectedDoc(null); }}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </ErrorBoundary>
  );
}

function MetaField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-secondary/30 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-medium truncate">{value}</p>
    </div>
  );
}
