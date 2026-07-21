"use client";

import { useState, useEffect } from "react";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton";
import toast from "react-hot-toast";
import { Settings, Cpu, Shield, RefreshCw, CheckCircle2 } from "lucide-react";

import type { SettingsResponse } from "@/services/settings";

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [edits, setEdits] = useState<Record<string, string>>({});

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const mod = await import("@/services/settings");
        const data = await mod.getSettings();
        setSettings(data);
      } catch {
        // settings endpoint may not exist - show placeholder
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
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
                  <InfoRow label="Version" value="1.0.0" />
                  <InfoRow label="LLM Provider" value="Groq (llama-3.3-70b-versatile)" />
                  <InfoRow label="Embedding Model" value="BAAI/bge-small-en-v1.5" />
                  <InfoRow label="Vector Database" value="Qdrant" />
                  <InfoRow label="Database" value="PostgreSQL 16" />
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </ErrorBoundary>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-secondary/30 transition-colors">
      <span className="text-sm">{label}</span>
      <span className="text-sm text-muted-foreground">{value}</span>
    </div>
  );
}
