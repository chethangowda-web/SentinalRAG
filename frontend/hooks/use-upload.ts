"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadDocument, embedDocument } from "@/services/ingest";
import type { IngestResponse } from "@/types";

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
      await embedDocument(result.document_id);
      setStep("done");
      return result;
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
