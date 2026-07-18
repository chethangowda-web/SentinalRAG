import { api } from "./api";
import type { IngestResponse } from "@/types";

export async function uploadDocument(file: File, onProgress?: (pct: number) => void): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await api.post<IngestResponse>("/api/v1/ingest", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });
  return data;
}

export async function embedDocument(documentId: string): Promise<{ document_id: string; total_chunks: number; embedded_chunks: number; status: string }> {
  const { data } = await api.post(`/api/v1/embed/${documentId}`);
  return data;
}
