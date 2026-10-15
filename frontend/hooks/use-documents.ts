"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listDocuments, getDocumentChunks, deleteDocument, reindexDocument } from "@/services/documents";
import toast from "react-hot-toast";

export function useDocuments() {
  return useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    // Poll quickly while something is being indexed in the background, slowly otherwise.
    refetchInterval: (query) => (query.state.data?.some((d) => d.status === "embedding") ? 3000 : 15000),
  });
}

export function useReindexDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reindexDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Indexing started");
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "Could not start indexing");
    },
  });
}

export function useDocumentChunks(documentId: string | null) {
  return useQuery({
    queryKey: ["document-chunks", documentId],
    queryFn: () => getDocumentChunks(documentId!),
    enabled: !!documentId,
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Document deleted");
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "Failed to delete document");
    },
  });
}
