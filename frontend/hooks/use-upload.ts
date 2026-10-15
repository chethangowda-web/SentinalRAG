"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadDocument } from "@/services/ingest";
import { getDocument } from "@/services/documents";
import type { IngestResponse } from "@/types";

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 10 * 60 * 1000;

async function waitUntilIndexed(documentId: string) {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const doc = await getDocument(documentId);
    if (doc.status === "embedded") return doc;
    if (doc.status === "failed") {
      throw new Error("Indexing failed. The document was saved; open Documents and choose Retry indexing.");
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
  throw new Error("Indexing is taking longer than expected. It continues in the background; check Documents shortly.");
}

export function useUpload() {
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState<"idle" | "uploading" | "embedding" | "done" | "error">("idle");
  const queryClient = useQueryClient();

  const upload = useMutation<IngestResponse, Error, File>({
    mutationFn: async (file: File) => {
      setStep("uploading");
      const result = await uploadDocument(file, (pct) => setProgress(pct));
      setStep("embedding");
      setProgress(0);
      // The server chunks and embeds in the background; wait for it, but a closed tab does not stop it.
      const indexed = await waitUntilIndexed(result.document_id);
      setStep("done");
      return { ...result, total_chunks: indexed.chunk_count, embedded_chunks: indexed.chunk_count };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: () => {
      setStep("error");
    },
  });

  return { upload, progress, step, reset: () => setStep("idle") };
}
