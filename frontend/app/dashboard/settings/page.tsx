"use client";

import { useState, useEffect } from "react";
import { Shield, Cpu, Layers, Sliders, Repeat, Database, Box, Tag, Save, RotateCcw, Wifi, CheckCircle, XCircle, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { getSettings, updateSettings, resetSettings, getSettingsHealth, type SettingsResponse } from "@/services/settings";

function SettingsContent() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [healthTest, setHealthTest] = useState<Record<string, { status: string; version?: string; error?: string; model?: string }> | null>(null);
  const [healthTesting, setHealthTesting] = useState(false);
  const [edits, setEdits] = useState<Record<string, string>>({});

  useEffect(() => {
    getSettings()
      .then((s) => {
        setSettings(s);
        setEdits({
          chunk_size: String(s.chunk_size),
          chunk_overlap: String(s.chunk_overlap),
          llm_temperature: String(s.llm_temperature),
          max_retries: String(s.max_retries),
          ocr_language: s.ocr_language,
        });
      })
      .catch(() => toast.error("Failed to load settings"))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const body = {
        chunk_size: parseInt(edits.chunk_size) || undefined,
        chunk_overlap: parseInt(edits.chunk_overlap) || undefined,
        llm_temperature: parseFloat(edits.llm_temperature) || undefined,
        max_retries: parseInt(edits.max_retries) || undefined,
        ocr_language: edits.ocr_language || undefined,
      };
      const updated = await updateSettings(body);
      setSettings(updated);
      toast.success("Settings saved");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      await resetSettings();
      const s = await getSettings();
      setSettings(s);
      setEdits({
        chunk_size: String(s.chunk_size),
        chunk_overlap: String(s.chunk_overlap),
        llm_temperature: String(s.llm_temperature),
        max_retries: String(s.max_retries),
        ocr_language: s.ocr_language,
      });
      toast.success("Settings reset to defaults");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to reset settings");
    }
  };

  const handleHealthTest = async () => {
    setHealthTesting(true);
    try {
      const result = await getSettingsHealth();
      setHealthTest(result);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Health check failed");
    } finally {
      setHealthTesting(false);
    }
  };

  if (loading) {
    return <LoadingSkeleton type="detail" count={3} />;
  }

  const editableFields = [
    { key: "chunk_size", label: "Chunk Size", description: "Tokens per chunk", icon: Layers, suffix: " tokens" },
    { key: "chunk_overlap", label: "Chunk Overlap", description: "Context preservation", icon: Sliders, suffix: " tokens" },
    { key: "llm_temperature", label: "LLM Temperature", description: "Response creativity", icon: Sliders, suffix: "" },
    { key: "max_retries", label: "Max Retries", description: "Self-correction loop", icon: Repeat, suffix: "" },
    { key: "ocr_language", label: "OCR Language", description: "Tesseract language pack", icon: Tag, suffix: "" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground">System configuration</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleReset}>
            <RotateCcw className="mr-1 h-3 w-3" /> Reset
          </Button>
          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Save className="mr-1 h-3 w-3" />}
            Save
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5 text-primary" />
              Editable Configuration
            </CardTitle>
            <CardDescription>Changes are saved to user_settings.json and take effect on next restart</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {editableFields.map((field) => {
              const Icon = field.icon;
              return (
                <div key={field.key}>
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 rounded-lg bg-primary/10 p-2">
                      <Icon className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{field.label}</p>
                      <Input
                        value={edits[field.key] ?? ""}
                        onChange={(e) => setEdits((prev) => ({ ...prev, [field.key]: e.target.value }))}
                        className="mt-1 h-8 text-sm"
                      />
                      <p className="mt-0.5 text-xs text-muted-foreground">{field.description}</p>
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
                <span className="text-sm text-muted-foreground">Embedding Model</span>
                <span className="text-sm font-medium">{settings?.embedding_model}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">LLM Model</span>
                <span className="text-sm font-medium">{settings?.llm_model}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Qdrant Collection</span>
                <span className="text-sm font-medium">{settings?.qdrant_collection}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Rate Limit</span>
                <span className="text-sm font-medium">{settings?.rate_limit_max_requests} req / {settings?.rate_limit_window_seconds}s</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">API Key Configured</span>
                <StatusBadge status={settings?.deepseek_api_key_set ? "healthy" : "error"} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Wifi className="h-5 w-5 text-primary" />
                Connection Test
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" onClick={handleHealthTest} disabled={healthTesting} className="mb-3">
                {healthTesting ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Wifi className="mr-1 h-3 w-3" />}
                Test Connections
              </Button>
              {healthTest && (
                <div className="space-y-2">
                  {Object.entries(healthTest).map(([name, status]) => (
                    <div key={name} className="flex items-center justify-between rounded-lg bg-secondary/50 p-2 text-sm">
                      <span className="capitalize">{name}</span>
                      <div className="flex items-center gap-2">
                        {status.status === "healthy" || status.status === "configured" ? (
                          <CheckCircle className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-xs text-muted-foreground">
                          {status.status === "healthy"
                            ? "OK"
                            : status.status === "configured"
                            ? status.model || "Configured"
                            : status.error || status.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
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
