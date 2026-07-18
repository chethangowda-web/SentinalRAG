"use client";

import { Shield, Cpu, Layers, Sliders, Repeat, Database, Box, Tag } from "lucide-react";
import { useHealth } from "@/hooks/use-health";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/shared/StatusBadge";

const configItems = [
  { label: "Embedding Model", value: "BAAI/bge-small-en-v1.5", icon: Cpu, description: "384-dimensional vectors" },
  { label: "LLM", value: "DeepSeek V4 (deepseek-chat)", icon: Box, description: "Temperature: 0.1" },
  { label: "Chunk Size", value: "500 tokens", icon: Layers, description: "Semantic chunking" },
  { label: "Chunk Overlap", value: "100 tokens", icon: Sliders, description: "Context preservation" },
  { label: "Confidence Threshold", value: "HIGH ≥ 80, MEDIUM ≥ 50", icon: Tag, description: "3-tier scoring" },
  { label: "Max Retries", value: "2", icon: Repeat, description: "Self-correction loop" },
  { label: "Qdrant Collection", value: "documents", icon: Database, description: "Vector search index" },
  { label: "RRF K Constant", value: "60", icon: Sliders, description: "Hybrid fusion" },
];

function SettingsContent() {
  const { data: health } = useHealth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">System configuration (read-only)</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-primary" />
              System Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {configItems.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label}>
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 rounded-lg bg-primary/10 p-2">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="text-sm text-foreground/80">{item.value}</p>
                      <p className="text-xs text-muted-foreground">{item.description}</p>
                    </div>
                  </div>
                  <Separator className="mt-3" />
                </div>
              );
            })}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                System Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Backend Status</span>
                <StatusBadge status={health?.status || "unknown"} />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Version</span>
                <span className="text-sm font-medium">{health?.version || "---"}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Application</span>
                <span className="text-sm font-medium">SentinelRAG Backend</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Box className="h-5 w-5 text-primary" />
                Pipeline Architecture
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {[
                  "Document Ingestion (OCR + Extraction)",
                  "Semantic Chunking (500 tokens)",
                  "Embedding Generation (bge-small-en-v1.5)",
                  "Qdrant Vector Indexing",
                  "Hybrid Retrieval (Vector + BM25 + RRF)",
                  "Cross-Encoder Reranking",
                  "Confidence Scoring (3-tier)",
                  "Self-Correction Loop (up to 2 retries)",
                  "Contradiction Detection",
                  "Answer Generation",
                ].map((step, i) => (
                  <div key={step} className="flex items-center gap-2 text-sm">
                    <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
                      {i + 1}
                    </div>
                    <span className="text-muted-foreground">{step}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ErrorBoundary>
      <SettingsContent />
    </ErrorBoundary>
  );
}
