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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
} from "lucide-react";
import type { Document } from "@/types";

type SortBy = "date" | "name" | "status";

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

function DocTypeBadge({ type }: { type?: string | null }) {
  if (!type || type === "unknown" || type === "other") return null;
  return (
    <Badge variant="secondary" className="text-[10px] capitalize">
      <BookOpen className="h-3 w-3 mr-1" />
      {type.replace(/_/g, " ")}
    </Badge>
  );
}

export default function DocumentsPage() {
  const { data: documents, isLoading } = useDocuments();
  const deleteDoc = useDeleteDocument();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<SortBy>("date");
  const [filterType, setFilterType] = useState<string>("all");
  const [filterOcr, setFilterOcr] = useState<string>("all");
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const { data: chunks } = useDocumentChunks(selectedDoc?.id ?? null);

  const docTypes = useMemo(() => {
    const types = new Set<string>();
    documents?.forEach((d) => { if (d.document_type) types.add(d.document_type); });
    return ["all", ...Array.from(types).sort()];
  }, [documents]);

  const filtered = useMemo(() => {
    return (documents ?? [])
      .filter((doc) => {
        if (filterType !== "all" && doc.document_type !== filterType) return false;
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
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
  }, [documents, search, sortBy, filterType, filterOcr]);

  const handleDelete = async (id: string, filename: string) => {
    try {
      await deleteDoc.mutateAsync(id);
      toast.success(`Deleted "${filename}"`);
    } catch {
      toast.error("Failed to delete document");
    }
  };

  const ocrOptions = ["all", "excellent", "good", "fair", "poor", "very_poor"];

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
        </div>

        <div className="flex flex-wrap items-start sm:items-center gap-3">
          <div className="relative w-full sm:w-64">
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
              <Button key={s} variant={sortBy === s ? "default" : "outline"} size="sm" onClick={() => setSortBy(s)}>
                {s === "date" && <Calendar className="mr-1.5 h-3.5 w-3.5" />}
                {s === "name" && <FileText className="mr-1.5 h-3.5 w-3.5" />}
                {s === "status" && <BarChart3 className="mr-1.5 h-3.5 w-3.5" />}
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </Button>
            ))}
          </div>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-36">
              <Filter className="h-3 w-3 mr-2" />
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              {docTypes.map((t) => (
                <SelectItem key={t} value={t}>{t === "all" ? "All Types" : t.replace(/_/g, " ")}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={filterOcr} onValueChange={setFilterOcr}>
            <SelectTrigger className="w-36">
              <Scan className="h-3 w-3 mr-2" />
              <SelectValue placeholder="OCR Quality" />
            </SelectTrigger>
            <SelectContent>
              {ocrOptions.map((o) => (
                <SelectItem key={o} value={o}>{o === "all" ? "All Quality" : o.replace(/_/g, " ")}</SelectItem>
              ))}
            </SelectContent>
          </Select>
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
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 shrink-0">
                            <File className="h-5 w-5 text-primary" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium leading-tight truncate">{doc.filename}</p>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {doc.file_type?.toUpperCase() || "PDF"}
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="shrink-0 -mr-2 -mt-1"
                          onClick={(e) => { e.stopPropagation(); handleDelete(doc.id, doc.filename); }}
                        >
                          <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                        </Button>
                      </div>

                      <Separator className="my-3" />

                      <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <Hash className="h-3 w-3" />
                          <span>{doc.word_count?.toLocaleString() ?? 0} words</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Layers className="h-3 w-3" />
                          <span>{doc.chunk_count ?? "--"} chunks</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Database className="h-3 w-3" />
                          <span>{doc.status === "embedded" ? "Embedded" : doc.status}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Scan className="h-3 w-3" />
                          <span>{doc.ocr_quality ? doc.ocr_quality.replace(/_/g, " ") : (doc.ocr_used ? "Done" : "No OCR")}</span>
                        </div>
                      </div>

                      <Separator className="my-3" />

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <StatusBadge status={doc.status} />
                          <OcrBadge quality={doc.ocr_quality} />
                          <DocTypeBadge type={doc.document_type} />
                        </div>
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
            description={search ? "Try a different search term or filter." : "Upload your first document to get started with RAG."}
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
                {selectedDoc?.file_type?.toUpperCase() || "PDF"} · {selectedDoc?.word_count?.toLocaleString() ?? 0} words · {selectedDoc?.pages ?? "--"} pages
                {selectedDoc?.estimated_reading_time ? ` · ${selectedDoc.estimated_reading_time} min read` : ""}
              </DialogDescription>
            </DialogHeader>

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
                    <div className="rounded-lg bg-secondary/30 p-4">
                      <p className="text-sm leading-relaxed">{selectedDoc.summary}</p>
                    </div>
                    {selectedDoc.key_topics && selectedDoc.key_topics.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">Key Topics</p>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedDoc.key_topics.map((topic) => (
                            <Badge key={topic} variant="secondary" className="text-xs">
                              {topic}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    {selectedDoc.keywords && selectedDoc.keywords.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">Keywords</p>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedDoc.keywords.map((kw) => (
                            <Badge key={kw} variant="outline" className="text-xs">
                              {kw}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-8 text-center">No summary available.</p>
                )}
              </TabsContent>

              <TabsContent value="chunks" className="mt-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-medium">{chunks?.chunks?.length ?? 0} chunks</span>
                  <StatusBadge status={selectedDoc?.status ?? ""} />
                </div>
                <ScrollArea className="h-[300px]">
                  <div className="space-y-2">
                    {chunks?.chunks?.map((chunk, i) => (
                      <Card key={chunk.id} className="bg-secondary/30">
                        <CardContent className="p-3">
                          <div className="flex items-start gap-3">
                            <span className="text-xs font-mono text-muted-foreground shrink-0 mt-0.5">#{i + 1}</span>
                            <div className="min-w-0">
                              <p className="text-xs text-muted-foreground line-clamp-3">{chunk.chunk_text}</p>
                              <div className="flex items-center gap-2 mt-1.5">
                                {chunk.page_number && <Badge variant="outline" className="text-[10px]">Page {chunk.page_number}</Badge>}
                                <Badge variant="outline" className="text-[10px]">{chunk.word_count ?? 0} words</Badge>
                                <Badge variant={chunk.embedding_status === "embedded" ? "success" : "outline"} className="text-[10px]">
                                  {chunk.embedding_status}
                                </Badge>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                    {(!chunks?.chunks || chunks.chunks.length === 0) && (
                      <p className="text-sm text-muted-foreground text-center py-8">No chunks available</p>
                    )}
                  </div>
                </ScrollArea>
              </TabsContent>

              <TabsContent value="metadata" className="mt-4">
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <MetaField label="File Type" value={selectedDoc?.file_type?.toUpperCase() || "PDF"} />
                    <MetaField label="File Size" value={selectedDoc?.file_size ? `${(selectedDoc.file_size / 1024).toFixed(1)} KB` : "--"} />
                    <MetaField label="Pages" value={selectedDoc?.pages?.toString() ?? "--"} />
                    <MetaField label="Words" value={selectedDoc?.word_count?.toLocaleString() ?? "0"} />
                    <MetaField label="Characters" value={selectedDoc?.char_count?.toLocaleString() ?? "0"} />
                    <MetaField label="Reading Time" value={selectedDoc?.estimated_reading_time ? `${selectedDoc.estimated_reading_time} min` : "--"} />
                    <MetaField label="OCR" value={selectedDoc?.ocr_used ? "Applied" : "Not Required"} />
                    <MetaField label="OCR Quality" value={selectedDoc?.ocr_quality?.replace(/_/g, " ") ?? "--"} />
                    <MetaField label="Document Type" value={selectedDoc?.document_type?.replace(/_/g, " ") ?? "--"} />
                    <MetaField label="Chunks" value={selectedDoc?.chunk_count?.toString() ?? "--"} />
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
                      <p className="text-sm text-muted-foreground text-center py-8">No preview available</p>
                    )}
                  </div>
                </ScrollArea>
              </TabsContent>
            </Tabs>
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
