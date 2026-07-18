"use client";

import { useQuery } from "@tanstack/react-query";
import { listDocuments, getDocumentChunks } from "@/services/documents";

export function useDocuments() {
  return useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    refetchInterval: 15000,
  });
}

export function useDocumentChunks(documentId: string | null) {
  return useQuery({
    queryKey: ["document-chunks", documentId],
    queryFn: () => getDocumentChunks(documentId!),
    enabled: !!documentId,
  });
}
