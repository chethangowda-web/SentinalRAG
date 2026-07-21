"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useUpload } from "@/hooks/use-upload";
import { UploadDropzone } from "@/components/shared/UploadDropzone";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import {
  Upload,
  CheckCircle2,
  FileText,
  Brain,
  Search,
  Database,
} from "lucide-react";

const pipelineSteps = [
  { key: "uploading", label: "Uploading", icon: Upload },
  { key: "extracting", label: "Extracting Text", icon: FileText },
  { key: "chunking", label: "Chunking", icon: Brain },
  { key: "embedding", label: "Generating Embeddings", icon: Search },
  { key: "indexing", label: "Indexing", icon: Database },
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
            Upload PDF, PNG, or JPG files for processing and indexing.
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
                  <CardTitle className="text-base">Processing Pipeline</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Progress value={progressPercent} className="h-2" />
                  <div className="space-y-2">
                    {pipelineSteps.map((s, i) => {
                      const isActive = step === s.key;
                      const isDone = stepIndex > i;
                      const Icon = s.icon;
                      return (
                        <div
                          key={s.key}
                          className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
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
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Upload Progress</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Transferring...</span>
                    <span className="font-medium">{Math.round(progress)}%</span>
                  </div>
                  <Progress value={progress} className="h-2 mt-2" />
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
                <CardContent>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="rounded-lg bg-secondary/50 p-3 text-center">
                      <p className="text-lg font-bold text-foreground">{upload.data.pages}</p>
                      <p className="text-xs text-muted-foreground">Pages</p>
                    </div>
                    <div className="rounded-lg bg-secondary/50 p-3 text-center">
                      <p className="text-lg font-bold text-foreground">
                        {upload.data.words?.toLocaleString() ?? "--"}
                      </p>
                      <p className="text-xs text-muted-foreground">Words</p>
                    </div>
                    <div className="rounded-lg bg-secondary/50 p-3 text-center">
                      <p className="text-lg font-bold text-foreground">
                        {upload.data.ocr_used ? "Yes" : "No"}
                      </p>
                      <p className="text-xs text-muted-foreground">OCR Used</p>
                    </div>
                    <div className="rounded-lg bg-secondary/50 p-3 text-center">
                      <p className="text-lg font-bold text-foreground">
                        {upload.data.processing_time?.toFixed(1) ?? "--"}s
                      </p>
                      <p className="text-xs text-muted-foreground">Processing Time</p>
                    </div>
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
