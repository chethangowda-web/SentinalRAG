"use client";

import { useState, useCallback, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { runEvaluation, getEvaluationStatus, getEvaluationLatest, setupBenchmark, getEvaluationHistory, getEvaluationDashboard } from "@/services/evaluation";
import type { EvalStatusResponse } from "@/services/evaluation";

export function useEvaluationLatest() {
  return useQuery({
    queryKey: ["evaluation-latest"],
    queryFn: getEvaluationLatest,
    // Poll while a run is in flight or the sample documents are still being indexed.
    refetchInterval: (query) => {
      const d = query.state.data;
      return d && (d.run?.status === "running" || d.benchmark.loading) ? 3000 : false;
    },
  });
}

export function useEvaluationReport() {
  const query = useEvaluationLatest();
  return { ...query, data: query.data?.report ?? undefined };
}

export function useSetupBenchmark() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: setupBenchmark,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["evaluation-latest"] }),
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
            queryClient.invalidateQueries({ queryKey: ["evaluation-latest"] });
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
    mutationFn: (full: boolean = false) => runEvaluation(full),
    onSuccess: (data) => {
      setStatus({ evaluation_id: data.evaluation_id, status: "running", progress: 0, total: data.total_questions, error: null });
      queryClient.invalidateQueries({ queryKey: ["evaluation-latest"] });
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

export function useEvaluationDashboard() {
  return useQuery({
    queryKey: ["evaluation-dashboard"],
    queryFn: getEvaluationDashboard,
    retry: 1,
  });
}
