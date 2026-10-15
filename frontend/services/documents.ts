import { api } from "./api";
import type { Document, ChunkListResponse } from "@/types";

export async function listDocuments(): Promise<Document[]> {
  const { data } = await api.get<Document[]>("/api/v1/documents");
  return data;
}

export async function getDocumentChunks(documentId: string): Promise<ChunkListResponse> {
  const { data } = await api.get<ChunkListResponse>(`/api/v1/document/${documentId}/chunks`);
  return data;
}

export async function getDocument(documentId: string): Promise<Document & { chunk_count: number }> {
  const { data } = await api.get(`/api/v1/documents/${documentId}`);
  return data;
}

export async function reindexDocument(documentId: string): Promise<{ status: string }> {
  const { data } = await api.post(`/api/v1/documents/${documentId}/reindex`);
  return data;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/api/v1/documents/${documentId}`);
}
