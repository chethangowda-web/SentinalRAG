"use client";

import toast from "react-hot-toast";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, AlertCircle, Loader2, FileText, Layers } from "lucide-react";
import { UploadDropzone } from "@/components/shared/UploadDropzone";
import { useUpload } from "@/hooks/use-upload";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

function UploadContent() {
  const { upload, progress, step, reset } = useUpload();

  const handleUpload = async (file: File) => {
    try {
      const result = await upload.mutateAsync(file);
      toast.success(`Document "${file.name}" processed successfully!`);
      setTimeout(reset, 3000);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Upload Document</h1>
        <p className="text-sm text-muted-foreground">Upload and process documents for retrieval</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Document Upload</CardTitle>
            </CardHeader>
            <CardContent>
              <UploadDropzone
                onUpload={handleUpload}
                progress={progress}
                isUploading={step === "uploading" || step === "embedding"}
                disabled={step === "embedding"}
              />

              <AnimatePresence>
                {step !== "idle" && step !== "error" && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-6 space-y-3"
                  >
                    <Separator />
                    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Processing Pipeline</p>
                    <div className="space-y-2">
                      {[
                        { label: "Uploading", done: step === "embedding" || step === "done", active: step === "uploading" },
                        { label: "Extracting Text", done: step === "embedding" || step === "done", active: step === "uploading" },
                        { label: "Chunking", done: step === "embedding" || step === "done", active: step === "uploading" },
                        { label: "Generating Embeddings", done: step === "done", active: step === "embedding" },
                        { label: "Indexing in Qdrant", done: step === "done", active: step === "embedding" },
                      ].map((s) => (
                        <div key={s.label} className="flex items-center gap-3 text-sm">
                          {s.done ? (
                            <CheckCircle className="h-4 w-4 text-emerald-500" />
                          ) : s.active ? (
                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                          ) : (
                            <div className="h-4 w-4 rounded-full border border-muted-foreground/30" />
                          )}
                          <span className={s.done ? "text-emerald-500" : s.active ? "text-foreground" : "text-muted-foreground"}>
                            {s.label}
                          </span>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {step === "error" && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4 flex items-center gap-2 rounded-lg bg-red-500/10 p-3 text-sm text-red-500">
                  <AlertCircle className="h-4 w-4" />
                  Upload failed. Please try again.
                </motion.div>
              )}

              {upload.data && step === "done" && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4">
                  <div className="flex items-center gap-2 text-emerald-500">
                    <CheckCircle className="h-5 w-5" />
                    <span className="text-sm font-medium">Document Processed Successfully</span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-1 sm:gap-3 text-center text-xs">
                    <div className="rounded bg-background/50 p-2">
                      <p className="font-medium text-foreground">{upload.data.pages}</p>
                      <p className="text-muted-foreground">Pages</p>
                    </div>
                    <div className="rounded bg-background/50 p-2">
                      <p className="font-medium text-foreground">{upload.data.words}</p>
                      <p className="text-muted-foreground">Words</p>
                    </div>
                    <div className="rounded bg-background/50 p-2">
                      <p className="font-medium text-foreground">{upload.data.ocr_used ? "Yes" : "No"}</p>
                      <p className="text-muted-foreground">OCR Used</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Supported Formats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {["PDF", "PNG", "JPG", "JPEG"].map((fmt) => (
                <div key={fmt} className="flex items-center gap-2 rounded-lg bg-secondary/50 p-2.5 text-sm">
                  <FileText className="h-4 w-4 text-primary" />
                  <span>{fmt}</span>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Processing</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="flex items-center justify-between">
                <span>Max file size</span>
                <span className="font-medium text-foreground">50 MB</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span>Chunk size</span>
                <span className="font-medium text-foreground">500 tokens</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span>Chunk overlap</span>
                <span className="font-medium text-foreground">100 tokens</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span>Embedding model</span>
                <span className="font-medium text-foreground">bge-small-en-v1.5</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default function UploadPage() {
  return (
    <ErrorBoundary>
      <UploadContent />
    </ErrorBoundary>
  );
}
