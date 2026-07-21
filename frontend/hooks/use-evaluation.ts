"use client";

import { useState, useCallback, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { runEvaluation, getEvaluationStatus, getEvaluationReport, getEvaluationHistory } from "@/services/evaluation";
import type { EvalStatusResponse } from "@/services/evaluation";

export function useEvaluationReport() {
  return useQuery({
    queryKey: ["evaluation-report"],
    queryFn: getEvaluationReport,
    retry: 1,
  });
}

export function useEvaluationHistory() {
  return useQuery({
    queryKey: ["evaluation-history"],
    queryFn: getEvaluationHistory,
  });
}

export function useRunEvaluation() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<EvalStatusResponse | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startPolling = useCallback((evalId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = setInterval(async () => {
      try {
        const s = await getEvaluationStatus(evalId);
        setStatus(s);
        if (s.status === "completed" || s.status === "failed") {
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = null;
          if (s.status === "completed") {
            queryClient.invalidateQueries({ queryKey: ["evaluation-report"] });
            queryClient.invalidateQueries({ queryKey: ["evaluation-history"] });
          }
        }
      } catch {
        if (pollingRef.current) clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }, 3000);
  }, [queryClient]);

  const mutation = useMutation({
    mutationFn: runEvaluation,
    onSuccess: (data) => {
      setStatus({ evaluation_id: data.evaluation_id, status: "running", progress: 0, total: data.total_questions, error: null });
      startPolling(data.evaluation_id);
    },
  });

  const resetStatus = useCallback(() => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    pollingRef.current = null;
    setStatus(null);
  }, []);

  return { ...mutation, evalStatus: status, resetStatus };
}
