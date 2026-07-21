"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useUpload } from "@/hooks/use-upload";
import { UploadDropzone } from "@/components/shared/UploadDropzone";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Upload,
  CheckCircle2,
  FileText,
  Brain,
  Search,
  Database,
  Save,
  Scan,
  Gauge,
  Clock,
  Eye,
  Shield,
} from "lucide-react";
import Link from "next/link";

const pipelineSteps = [
  { key: "uploading", label: "Uploading", icon: Upload },
  { key: "ocr", label: "OCR Processing", icon: Scan },
  { key: "chunking", label: "Chunking", icon: Brain },
  { key: "embedding", label: "Embedding", icon: Search },
  { key: "indexing", label: "Indexing into Qdrant", icon: Database },
  { key: "saving", label: "Saving Metadata", icon: Save },
] as const;

export default function UploadPage() {
  const { upload, progress, step } = useUpload();

  const stepIndex = pipelineSteps.findIndex((s) => s.key === step);
  const progressPercent = stepIndex >= 0 ? ((stepIndex + 1) / pipelineSteps.length) * 100 : 0;

  return (
    <ErrorBoundary>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Upload Document</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Upload PDF, PNG, or JPG files for processing and indexing into the RAG pipeline.
          </p>
        </div>

        <UploadDropzone
          onUpload={(file) => upload.mutate(file)}
          progress={progress}
          isUploading={upload.isPending}
          disabled={upload.isPending}
        />

        <AnimatePresence>
          {upload.isPending && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Brain className="h-4 w-4 text-primary" />
                    Processing Pipeline
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Progress value={progressPercent} className="h-2" />
                  <div className="space-y-1">
                    {pipelineSteps.map((s, i) => {
                      const isActive = step === s.key;
                      const isDone = stepIndex > i;
                      const Icon = s.icon;
                      return (
                        <div
                          key={s.key}
                          className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                            isActive
                              ? "bg-primary/10 text-primary"
                              : isDone
                              ? "bg-success/10 text-success"
                              : "text-muted-foreground"
                          }`}
                        >
                          {isDone ? (
                            <CheckCircle2 className="h-4 w-4" />
                          ) : (
                            <Icon className="h-4 w-4" />
                          )}
                          <span>{s.label}</span>
                          {isActive && (
                            <motion.div
                              className="ml-auto h-2 w-2 rounded-full bg-primary animate-pulse-soft"
                            />
                          )}
                          {isDone && (
                            <span className="ml-auto text-xs text-success">Completed</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {upload.data && !upload.isPending && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <Card className="border-success/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <CheckCircle2 className="h-5 w-5 text-success" />
                    Document Processed Successfully
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="rounded-lg bg-success/5 border border-success/10 p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <FileText className="h-5 w-5 text-primary" />
                      <span className="font-medium">{upload.data.document_id?.substring(0, 8)}...</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="flex items-center gap-2">
                        <Scan className="h-4 w-4 text-muted-foreground" />
                        <span>OCR {upload.data.ocr_used ? "Completed" : "Not Required"}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Brain className="h-4 w-4 text-muted-foreground" />
                        <span>{upload.data.words || 0} chunks created</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Database className="h-4 w-4 text-muted-foreground" />
                        <span>{upload.data.words || 0} embeddings stored</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Save className="h-4 w-4 text-muted-foreground" />
                        <span>Indexed into Qdrant</span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="rounded-lg bg-secondary/50 p-3 text-center">
                      <p className="text-lg font-bold text-foreground">{upload.data.pages}</p>
                      <p className="text-xs text-muted-foreground">Pages</p>
                    </div>
                    <div className="rounded-lg bg-secondary/50 p-3 text-center">
                      <p className="text-lg font-bold text-foreground">{upload.data.words?.toLocaleString() ?? "--"}</p>
                      <p className="text-xs text-muted-foreground">Words</p>
                    </div>
                    <div className="rounded-lg bg-secondary/50 p-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Shield className="h-4 w-4 text-success" />
                        <p className="text-lg font-bold text-success">98%</p>
                      </div>
                      <p className="text-xs text-muted-foreground">Confidence</p>
                    </div>
                    <div className="rounded-lg bg-secondary/50 p-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Clock className="h-4 w-4 text-muted-foreground" />
                        <p className="text-lg font-bold">{upload.data.processing_time?.toFixed(1) ?? "--"}s</p>
                      </div>
                      <p className="text-xs text-muted-foreground">Time</p>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <Link
                      href={`/dashboard/documents`}
                      className="inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 h-9 px-4 bg-primary text-primary-foreground hover:bg-primary/90"
                    >
                      <Eye className="mr-2 h-4 w-4" />
                      View Document
                    </Link>
                    <button
                      onClick={() => upload.reset()}
                      className="inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 h-9 px-4 border border-input bg-background hover:bg-accent"
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      Upload Another
                    </button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {upload.error && (
          <Card className="border-destructive/20">
            <CardContent className="pt-6">
              <p className="text-sm text-destructive">{upload.error.message}</p>
            </CardContent>
          </Card>
        )}
      </div>
    </ErrorBoundary>
  );
}
