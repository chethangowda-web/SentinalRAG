"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { runEvaluation, getEvaluationReport, getEvaluationHistory } from "@/services/evaluation";

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

  return useMutation({
    mutationFn: runEvaluation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluation-report"] });
      queryClient.invalidateQueries({ queryKey: ["evaluation-history"] });
    },
  });
}
