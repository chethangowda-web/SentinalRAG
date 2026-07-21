"use client";

import { useState, useEffect } from "react";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, XCircle, Minus } from "lucide-react";
import toast from "react-hot-toast";
import { Cpu, Shield, RefreshCw, Server, Database, Brain, Wifi, HardDrive, Zap, Clock, Activity } from "lucide-react";

import type { SettingsResponse } from "@/services/settings";

interface SystemHealth {
  backend: { status: string; version?: string; error?: string };
  qdrant: { status: string; error?: string };
  database: { status: string; error?: string };
  llm: { status: string; model?: string; error?: string };
  embedding?: { status: string; model?: string; error?: string };
  disk?: { upload_dir_mb?: number; processed_dir_mb?: number; total_mb?: number; error?: string };
  memory?: { total_mb?: number; available_mb?: number; used_mb?: number; percent?: number; error?: string };
}

function StatusIndicator({ status }: { status: string }) {
  if (status === "healthy" || status === "configured") return <CheckCircle2 className="h-4 w-4 text-success" />;
  if (status === "unhealthy") return <XCircle className="h-4 w-4 text-destructive" />;
  return <Minus className="h-4 w-4 text-muted-foreground" />;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [edits, setEdits] = useState<Record<string, string>>({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [mod, healthMod] = await Promise.all([
          import("@/services/settings"),
          import("@/services/settings"),
        ]);
        const [settingsData, healthRaw] = await Promise.all([
          mod.getSettings(),
          healthMod.getSettingsHealth(),
        ]);
        setSettings(settingsData);

        // also fetch /api/v1/metrics for disk/memory
        const { api } = await import("@/services/api");
        const { data: metricsData } = await api.get("/api/v1/metrics");

        setHealth({
          ...(healthRaw as unknown as SystemHealth),
          disk: metricsData?.disk,
          memory: metricsData?.memory,
        });
      } catch {
        // API might not be reachable - show what we have
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const mod = await import("@/services/settings");
      const payload: Record<string, string | number> = {};
      for (const [key, val] of Object.entries(edits)) {
        payload[key] = isNaN(Number(val)) ? val : Number(val);
      }
      await mod.updateSettings(payload);
      toast.success("Settings saved");
      setEdits({});
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const settingFields = [
    { key: "chunk_size", label: "Chunk Size", desc: "Maximum words per chunk", type: "number" },
    { key: "chunk_overlap", label: "Chunk Overlap", desc: "Words overlapping between chunks", type: "number" },
    { key: "llm_temperature", label: "LLM Temperature", desc: "Controls response randomness (0-2)", type: "number" },
    { key: "max_retries", label: "Max Retries", desc: "Maximum query rewrite retries", type: "number" },
    { key: "ocr_language", label: "OCR Language", desc: "Tesseract language code (e.g. eng)", type: "text" },
  ];

  const llmLabel = health?.llm?.model
    ? `Groq (${health.llm.model})`
    : (settings?.llm_model ?? "Unknown");

  const dbLabel = health?.database?.status === "healthy" ? "PostgreSQL (connected)" : "PostgreSQL (disconnected)";
  const qdrantLabel = health?.qdrant?.status === "healthy" ? "Qdrant (connected)" : "Qdrant (disconnected)";

  return (
    <ErrorBoundary>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure your RAG pipeline parameters.
          </p>
        </div>

        {loading ? (
          <LoadingSkeleton type="card" count={2} />
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Cpu className="h-4 w-4 text-primary" />
                  Pipeline Configuration
                </CardTitle>
                <CardDescription>
                  Adjust chunking, LLM, and OCR parameters for your use case.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {settingFields.map((field) => {
                  const currentVal = settings?.[field.key];
                  const editVal = edits[field.key] ?? (currentVal !== undefined ? String(currentVal) : "");
                  return (
                    <div key={field.key} className="grid gap-2">
                      <label className="text-sm font-medium">{field.label}</label>
                      <p className="text-xs text-muted-foreground">{field.desc}</p>
                      <Input
                        type={field.type}
                        value={editVal}
                        onChange={(e) =>
                          setEdits((prev) => ({ ...prev, [field.key]: e.target.value }))
                        }
                        className="max-w-xs"
                      />
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            <div className="flex items-center gap-3">
              <Button onClick={handleSave} disabled={saving || Object.keys(edits).length === 0}>
                {saving ? (
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                )}
                Save Changes
              </Button>
              {Object.keys(edits).length === 0 && (
                <span className="text-xs text-muted-foreground">No unsaved changes</span>
              )}
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Shield className="h-4 w-4 text-primary" />
                  System Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <InfoRow
                    label="Version"
                    value={health?.backend?.version ?? "1.0.0"}
                    icon={<Server className="h-4 w-4 text-muted-foreground" />}
                  />
                  <InfoRow label="LLM Provider" value={llmLabel} icon={<Brain className="h-4 w-4 text-muted-foreground" />}>
                    <StatusIndicator status={health?.llm?.status ?? "unknown"} />
                  </InfoRow>
                  <InfoRow
                    label="Embedding Model"
                    value={settings?.embedding_model ?? "BAAI/bge-small-en-v1.5"}
                    icon={<Zap className="h-4 w-4 text-muted-foreground" />}
                  />
                  <Separator />
                  <InfoRow label="Vector Database" value={qdrantLabel} icon={<Database className="h-4 w-4 text-muted-foreground" />}>
                    <StatusIndicator status={health?.qdrant?.status ?? "unknown"} />
                  </InfoRow>
                  <InfoRow label="Database" value={dbLabel} icon={<Database className="h-4 w-4 text-muted-foreground" />}>
                    <StatusIndicator status={health?.database?.status ?? "unknown"} />
                  </InfoRow>
                  <Separator />
                  {health?.memory?.total_mb != null && (
                    <InfoRow
                      label="Memory"
                      value={`${health.memory.used_mb?.toFixed(0) ?? "?"} MB / ${health.memory.total_mb.toFixed(0)} MB (${health.memory.percent?.toFixed(0) ?? "?"}%)`}
                      icon={<Activity className="h-4 w-4 text-muted-foreground" />}
                    />
                  )}
                  {health?.disk?.total_mb != null && (
                    <InfoRow
                      label="Storage"
                      value={`${health.disk.total_mb.toFixed(1)} MB used`}
                      icon={<HardDrive className="h-4 w-4 text-muted-foreground" />}
                    />
                  )}
                  {settings?.embedding_dimension != null && (
                    <InfoRow
                      label="Vector Dimension"
                      value={`${settings.embedding_dimension}`}
                      icon={<Wifi className="h-4 w-4 text-muted-foreground" />}
                    />
                  )}
                  {settings != null && (settings.rate_limit_max_requests ?? 0) > 0 && (
                    <InfoRow
                      label="Rate Limit"
                      value={`${settings.rate_limit_max_requests} req / ${settings.rate_limit_window_seconds}s`}
                      icon={<Clock className="h-4 w-4 text-muted-foreground" />}
                    />
                  )}
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </ErrorBoundary>
  );
}

function InfoRow({
  label,
  value,
  icon,
  children,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-secondary/30 transition-colors">
      <span className="flex items-center gap-2 text-sm">
        {icon}
        {label}
      </span>
      <span className="flex items-center gap-2 text-sm text-muted-foreground">
        {value}
        {children}
      </span>
    </div>
  );
}
