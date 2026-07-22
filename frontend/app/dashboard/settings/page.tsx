"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import toast from "react-hot-toast";
import {
  Cpu,
  Shield,
  RefreshCw,
  Server,
  Database,
  Brain,
  Wifi,
  HardDrive,
  Zap,
  Clock,
  Activity,
  CheckCircle2,
  XCircle,
  Minus,
  Sliders,
  Info,
  Settings2,
  FileText,
  Globe,
  Gauge,
  Layers,
  AlertTriangle,
  Save,
  Loader2,
  Scan,
  BookOpen,
} from "lucide-react";

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

function InfoRow({
  label,
  value,
  icon,
  children,
  status,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
  children?: React.ReactNode;
  status?: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg px-4 py-3 hover:bg-secondary/30 transition-colors">
      <span className="flex items-center gap-2 text-sm">
        {icon}
        {label}
      </span>
      <span className="flex items-center gap-2 text-sm text-muted-foreground">
        {value}
        {children}
        {status && <StatusIndicator status={status} />}
      </span>
    </div>
  );
}

function SettingField({
  label,
  desc,
  type,
  value,
  onChange,
}: {
  label: string;
  desc: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      <p className="text-xs text-muted-foreground">{desc}</p>
      <Input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="max-w-xs h-9"
      />
    </div>
  );
}

function StatusCard({ title, status, icon: Icon, details }: {
  title: string;
  status: string;
  icon: React.ElementType;
  details?: string;
}) {
  const statusConfig: Record<string, { color: string; bg: string; label: string }> = {
    healthy: { color: "text-success", bg: "bg-success/10", label: "Operational" },
    configured: { color: "text-success", bg: "bg-success/10", label: "Configured" },
    unhealthy: { color: "text-destructive", bg: "bg-destructive/10", label: "Unhealthy" },
    unavailable: { color: "text-muted-foreground", bg: "bg-muted", label: "Unavailable" },
  };
  const cfg = statusConfig[status] ?? statusConfig.unavailable;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 rounded-lg border p-3 transition-colors hover:bg-secondary/30"
    >
      <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${cfg.bg}`}>
        <Icon className={`h-4 w-4 ${cfg.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{title}</p>
        {details && <p className="text-[10px] text-muted-foreground truncate">{details}</p>}
      </div>
      <Badge variant="outline" className={`text-[10px] ${cfg.color}`}>{cfg.label}</Badge>
    </motion.div>
  );
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

        let metricsData: any = {};
        try {
          const { api } = await import("@/services/api");
          const { data } = await api.get("/api/v1/metrics");
          metricsData = data;
        } catch {
          // metrics endpoint may not be available
        }

        setHealth({
          ...(healthRaw as unknown as SystemHealth),
          disk: metricsData?.disk,
          memory: metricsData?.memory,
        });
      } catch {
        // API might not be reachable
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
      toast.success("Settings saved successfully");
      setEdits({});
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const isUnchanged = Object.keys(edits).length === 0;

  const llmModel = health?.llm?.model ?? settings?.llm_model ?? null;
  const embeddingModel = settings?.embedding_model ?? null;
  const ocrLanguage = settings?.ocr_language ?? null;
  const chunkSize = settings?.chunk_size ?? null;
  const topK = null; // Not available from API
  const storageUsed = health?.disk?.total_mb != null ? `${health.disk.total_mb.toFixed(1)} MB` : null;
  const memoryUsed = health?.memory?.percent != null ? `${health.memory.percent.toFixed(0)}%` : null;

  const settingFields = [
    { key: "chunk_size", label: "Chunk Size", desc: "Maximum words per chunk", type: "number" },
    { key: "chunk_overlap", label: "Chunk Overlap", desc: "Words overlapping between chunks", type: "number" },
    { key: "llm_temperature", label: "LLM Temperature", desc: "Controls response randomness (0-2)", type: "number" },
    { key: "max_retries", label: "Max Retries", desc: "Maximum query rewrite retries", type: "number" },
    { key: "ocr_language", label: "OCR Language", desc: "Tesseract language code (e.g. eng)", type: "text" },
  ];

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure your RAG pipeline and view system status.
          </p>
        </div>

        {loading ? (
          <div className="space-y-6">
            <LoadingSkeleton type="card" count={2} />
          </div>
        ) : (
          <Tabs defaultValue="configuration">
            <TabsList>
              <TabsTrigger value="configuration">
                <Sliders className="mr-2 h-4 w-4" />
                Configuration
              </TabsTrigger>
              <TabsTrigger value="system">
                <Server className="mr-2 h-4 w-4" />
                System Status
              </TabsTrigger>
            </TabsList>

            <TabsContent value="configuration" className="mt-6 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Settings2 className="h-4 w-4 text-primary" />
                    Pipeline Configuration
                  </CardTitle>
                  <CardDescription>
                    Adjust chunking, LLM, and OCR parameters. Changes take effect on the next document upload.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  {settingFields.map((field) => {
                    const currentVal = settings?.[field.key];
                    const editVal = edits[field.key] ?? (currentVal !== undefined ? String(currentVal) : "");
                    return (
                      <SettingField
                        key={field.key}
                        label={field.label}
                        desc={field.desc}
                        type={field.type}
                        value={editVal}
                        onChange={(v) => setEdits((prev) => ({ ...prev, [field.key]: v }))}
                      />
                    );
                  })}

                  <div className="flex items-center gap-3 pt-2">
                    <Button onClick={handleSave} disabled={saving || isUnchanged} className="gap-2">
                      {saving ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Save className="h-4 w-4" />
                      )}
                      Save Changes
                    </Button>
                    {isUnchanged && (
                      <span className="text-xs text-muted-foreground">No unsaved changes</span>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Info className="h-4 w-4 text-primary" />
                    Model Information
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <InfoRow
                      label="Current LLM"
                      value={llmModel ?? "Unavailable"}
                      icon={<Brain className="h-4 w-4 text-muted-foreground" />}
                    >
                      <StatusIndicator status={health?.llm?.status ?? "unavailable"} />
                    </InfoRow>
                    <InfoRow
                      label="Embedding Model"
                      value={embeddingModel ?? "Unavailable"}
                      icon={<Zap className="h-4 w-4 text-muted-foreground" />}
                    >
                      <StatusIndicator status={health?.embedding?.status ?? "unavailable"} />
                    </InfoRow>
                    <InfoRow
                      label="OCR Language"
                      value={ocrLanguage ?? "Unavailable"}
                      icon={<Scan className="h-4 w-4 text-muted-foreground" />}
                    />
                    <InfoRow
                      label="Retrieval Top-K"
                      value={topK ?? "Unavailable"}
                      icon={<Layers className="h-4 w-4 text-muted-foreground" />}
                    />
                    <InfoRow
                      label="Chunk Size"
                      value={chunkSize != null ? `${chunkSize} words` : "Unavailable"}
                      icon={<FileText className="h-4 w-4 text-muted-foreground" />}
                    />
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
            </TabsContent>

            <TabsContent value="system" className="mt-6 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Shield className="h-4 w-4 text-primary" />
                    System Health
                  </CardTitle>
                  <CardDescription>
                    Real-time status of all system components.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <StatusCard
                      title="Backend API"
                      status={health?.backend?.status ?? "unavailable"}
                      icon={Server}
                      details={health?.backend?.version ? `v${health.backend.version}` : undefined}
                    />
                    <StatusCard
                      title="Qdrant Vector Database"
                      status={health?.qdrant?.status ?? "unavailable"}
                      icon={Database}
                      details={health?.qdrant?.error ? `Error: ${health.qdrant.error}` : undefined}
                    />
                    <StatusCard
                      title="PostgreSQL Database"
                      status={health?.database?.status ?? "unavailable"}
                      icon={Database}
                      details={health?.database?.error ? `Error: ${health.database.error}` : undefined}
                    />
                    <StatusCard
                      title="LLM Provider (Groq)"
                      status={health?.llm?.status ?? "unavailable"}
                      icon={Brain}
                      details={health?.llm?.model ?? undefined}
                    />
                    <StatusCard
                      title="Embedding Service"
                      status={health?.embedding?.status ?? "unavailable"}
                      icon={Zap}
                      details={health?.embedding?.model ?? undefined}
                    />
                  </div>
                </CardContent>
              </Card>

              {(storageUsed || memoryUsed) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Activity className="h-4 w-4 text-primary" />
                      Resource Usage
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {storageUsed && (
                        <InfoRow
                          label="Storage Usage"
                          value={storageUsed}
                          icon={<HardDrive className="h-4 w-4 text-muted-foreground" />}
                        />
                      )}
                      {memoryUsed && (
                        <InfoRow
                          label="Memory Usage"
                          value={memoryUsed}
                          icon={<Activity className="h-4 w-4 text-muted-foreground" />}
                        />
                      )}
                      {health?.memory?.total_mb != null && (
                        <InfoRow
                          label="Total Memory"
                          value={`${health.memory.total_mb.toFixed(0)} MB`}
                          icon={<Cpu className="h-4 w-4 text-muted-foreground" />}
                        />
                      )}
                      {health?.memory?.available_mb != null && (
                        <InfoRow
                          label="Available Memory"
                          value={`${health.memory.available_mb.toFixed(0)} MB`}
                          icon={<Cpu className="h-4 w-4 text-muted-foreground" />}
                        />
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <RefreshCw className="h-4 w-4 text-primary" />
                    Data Management
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex gap-3">
                  <Button variant="outline" size="sm" className="gap-2" onClick={async () => {
                    try {
                      const mod = await import("@/services/settings");
                      await mod.resetSettings();
                      toast.success("Settings reset to defaults");
                    } catch {
                      toast.error("Failed to reset settings");
                    }
                  }}>
                    <RefreshCw className="h-4 w-4" />
                    Reset to Defaults
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </ErrorBoundary>
  );
}
