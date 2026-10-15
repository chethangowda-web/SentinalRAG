import axios from "axios";
import type { IngestResponse } from "@/types";
import { api, getStoredToken } from "./api";

// Empty means same origin (nginx or the backend serving this app). Never default to a real deployment.
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function uploadDocument(file: File, onProgress?: (pct: number) => void): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const token = getStoredToken();
  const { data } = await axios.post<IngestResponse>(`${BACKEND_URL}/api/v1/ingest`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
    timeout: 300000,
  });
  return data;
}

export async function embedDocument(documentId: string): Promise<{ document_id: string; total_chunks: number; embedded_chunks: number; status: string }> {
  const { data } = await api.post(`/api/v1/embed/${documentId}`);
  return data;
}
