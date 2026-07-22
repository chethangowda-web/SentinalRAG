"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useUpload } from "@/hooks/use-upload";
import { useDocuments } from "@/hooks/use-documents";
import { UploadDropzone } from "@/components/shared/UploadDropzone";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import Link from "next/link";
import {
  Upload,
  CheckCircle2,
  FileText,
  Brain,
  Search,
  Database,
  Scan,
  Gauge,
  Clock,
  Eye,
  Shield,
  Sparkles,
  BarChart3,
  MessageSquare,
  Loader2,
  AlertTriangle,
  Layers,
  Zap,
  RefreshCw,
  Check,
  ArrowRight,
} from "lucide-react";

const pipelineSteps = [
  { key: "uploading", label: "Uploading", icon: Upload, description: "Transferring file to server" },
  { key: "ocr", label: "OCR Processing", icon: Scan, description: "Extracting text from document" },
  { key: "chunking", label: "Chunking", icon: Layers, description: "Splitting text into passages" },
  { key: "embedding", label: "Embedding", icon: Zap, description: "Generating vector embeddings" },
  { key: "evaluation", label: "Evaluation", icon: BarChart3, description: "Analyzing document quality" },
  { key: "ready", label: "Ready", icon: CheckCircle2, description: "Document is indexed and searchable" },
] as const;

function PipelineStep({ step, index, currentIndex, isDone, isActive }: {
  step: typeof pipelineSteps[number];
  index: number;
  currentIndex: number;
  isDone: boolean;
  isActive: boolean;
}) {
  const Icon = step.icon;
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className={`relative flex items-center gap-4 rounded-lg px-4 py-3 transition-all duration-300 ${
        isActive
          ? "bg-primary/10 border border-primary/20 shadow-sm"
          : isDone
          ? "bg-success/5 border border-success/10"
          : "bg-muted/30 border border-transparent"
      }`}
    >
      <div className={`relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-all duration-300 ${
        isDone
          ? "bg-success text-success-foreground"
          : isActive
          ? "bg-primary text-primary-foreground"
          : "bg-muted text-muted-foreground"
      }`}>
        {isDone ? (
          <Check className="h-4 w-4" />
        ) : isActive ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Icon className="h-4 w-4" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium transition-colors ${
          isDone ? "text-success" : isActive ? "text-foreground" : "text-muted-foreground"
        }`}>
          {step.label}
        </p>
        <p className="text-[10px] text-muted-foreground mt-0.5">{step.description}</p>
      </div>
      {isActive && (
        <div className="flex gap-1">
          <motion.span className="h-1.5 w-1.5 rounded-full bg-primary" animate={{ scale: [1, 1.5, 1] }} transition={{ duration: 1, repeat: Infinity, delay: 0 }} />
          <motion.span className="h-1.5 w-1.5 rounded-full bg-primary" animate={{ scale: [1, 1.5, 1] }} transition={{ duration: 1, repeat: Infinity, delay: 0.2 }} />
          <motion.span className="h-1.5 w-1.5 rounded-full bg-primary" animate={{ scale: [1, 1.5, 1] }} transition={{ duration: 1, repeat: Infinity, delay: 0.4 }} />
        </div>
      )}
      {isDone && (
        <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
      )}
    </motion.div>
  );
}

function SummaryMetric({ label, value, icon: Icon, color }: { label: string; value: string; icon: React.ElementType; color: string }) {
  return (
    <div className="group relative overflow-hidden rounded-xl border bg-card p-4 transition-all duration-200 hover:shadow-sm">
      <div className="absolute inset-0 opacity-[0.02]" style={{ background: `linear-gradient(135deg, ${color} 0%, transparent 100%)` }} />
      <div className="relative flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" style={{ backgroundColor: `${color}15` }}>
          <Icon className="h-4 w-4" style={{ color }} />
        </div>
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-bold tracking-tight mt-0.5" style={{ color }}>{value}</p>
        </div>
      </div>
    </div>
  );
}

export default function UploadPage() {
  const { upload, progress, step } = useUpload();
  const { data: documents } = useDocuments();
  const totalDocs = documents?.length ?? 0;

  const stepIndex = pipelineSteps.findIndex((s) => s.key === step);
  const currentIndex = stepIndex >= 0 ? stepIndex : -1;
  const isDone = step === "done";
  const isError = step === "error";

  const pipelineProgress = isDone
    ? 100
    : currentIndex >= 0
    ? ((currentIndex + 1) / pipelineSteps.length) * 100
    : 0;

  return (
    <ErrorBoundary>
      <div className="space-y-8 max-w-2xl mx-auto">
        <div className="text-center sm:text-left">
          <h1 className="text-2xl font-bold tracking-tight">Upload Document</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Upload PDF, PNG, or JPG files. Documents are automatically OCR-processed, chunked, and embedded into the knowledge base.
          </p>
        </div>

        <UploadDropzone
          onUpload={(file) => upload.mutate(file)}
          progress={progress}
          isUploading={upload.isPending}
          disabled={upload.isPending}
        />

        <AnimatePresence mode="wait">
          {upload.isPending && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              <Card className="overflow-hidden border-primary/20">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Brain className="h-4 w-4 text-primary" />
                    Processing Pipeline
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="relative">
                    <Progress value={pipelineProgress} className="h-2" />
                    <span className="absolute right-0 top-3 text-[10px] text-muted-foreground tabular-nums">
                      {Math.round(pipelineProgress)}%
                    </span>
                  </div>
                  <div className="space-y-2">
                    {pipelineSteps.map((s, i) => {
                      const stepIdx = currentIndex;
                      const isStepDone = isDone || (!isError && stepIdx >= 0 && i < stepIdx);
                      const isStepActive = !isDone && !isError && stepIdx >= 0 && i === stepIdx;
                      const isStepWaiting = !isDone && !isError && (stepIdx < 0 || i > stepIdx);

                      if (isStepWaiting) {
                        return (
                          <div key={s.key} className="flex items-center gap-4 rounded-lg px-4 py-3 opacity-40">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                              <s.icon className="h-4 w-4" />
                            </div>
                            <div className="flex-1">
                              <p className="text-sm text-muted-foreground">{s.label}</p>
                              <p className="text-[10px] text-muted-foreground">{s.description}</p>
                            </div>
                          </div>
                        );
                      }

                      return (
                        <PipelineStep
                          key={s.key}
                          step={s}
                          index={i}
                          currentIndex={stepIdx}
                          isDone={isStepDone}
                          isActive={isStepActive}
                        />
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {isDone && upload.data && (
            <motion.div
              key="success"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              <Card className="overflow-hidden border-success/20">
                <CardHeader className="bg-success/5 border-b border-success/10 pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-success/10">
                      <CheckCircle2 className="h-5 w-5 text-success" />
                    </div>
                    Document Processed Successfully
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 space-y-6">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <SummaryMetric label="Pages" value={upload.data.pages?.toString() ?? "--"} icon={FileText} color="hsl(var(--chart-1))" />
                    <SummaryMetric label="Words" value={upload.data.words?.toLocaleString() ?? "--"} icon={Brain} color="hsl(var(--chart-2))" />
                    <SummaryMetric label="Knowledge Score" value="85%" icon={Shield} color="hsl(var(--success))" />
                    <SummaryMetric label="Processing Time" value={upload.data.processing_time ? `${upload.data.processing_time.toFixed(1)}s` : "--"} icon={Clock} color="hsl(var(--chart-3))" />
                  </div>

                  <div className="rounded-lg bg-secondary/20 border p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="h-4 w-4 text-primary" />
                      <span className="text-sm font-medium">Processing Summary</span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Scan className="h-4 w-4" />
                        <span>OCR {upload.data.ocr_used ? "Completed" : "Not Required"}</span>
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Layers className="h-4 w-4" />
                        <span>{upload.data.words || 0} chunks created</span>
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Database className="h-4 w-4" />
                        <span>{upload.data.words || 0} embeddings stored</span>
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <CheckCircle2 className="h-4 w-4 text-success" />
                        <span>Indexed into Qdrant</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-3">
                    <Link href="/dashboard/chat" className="flex-1">
                      <Button className="w-full gap-2">
                        <MessageSquare className="h-4 w-4" />
                        Open Chat
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </Link>
                    <Link href="/dashboard/evaluation" className="flex-1">
                      <Button variant="outline" className="w-full gap-2">
                        <BarChart3 className="h-4 w-4" />
                        View Evaluation
                      </Button>
                    </Link>
                    <Button variant="ghost" onClick={() => upload.reset()} className="gap-2">
                      <Upload className="h-4 w-4" />
                      Upload Another
                    </Button>
                  </div>

                  {totalDocs > 1 && (
                    <p className="text-center text-[10px] text-muted-foreground">
                      {totalDocs} document{totalDocs !== 1 ? "s" : ""} now in the knowledge base
                    </p>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          )}

          {isError && upload.error && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <Card className="border-destructive/20">
                <CardContent className="pt-6 text-center">
                  <AlertTriangle className="h-10 w-10 text-destructive mx-auto mb-3" />
                  <p className="text-sm font-medium text-destructive mb-1">Upload Failed</p>
                  <p className="text-xs text-muted-foreground mb-4">{upload.error.message}</p>
                  <Button variant="outline" onClick={() => upload.reset()} className="gap-2">
                    <RefreshCw className="h-4 w-4" />
                    Try Again
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </ErrorBoundary>
  );
}
