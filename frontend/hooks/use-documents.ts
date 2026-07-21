"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listDocuments, getDocumentChunks, deleteDocument } from "@/services/documents";
import toast from "react-hot-toast";

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
