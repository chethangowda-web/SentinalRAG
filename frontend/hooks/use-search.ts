"use client";

import { useMutation } from "@tanstack/react-query";
import { searchDocuments } from "@/services/search";
import type { SearchRequest, SearchResponse } from "@/types";

export function useSearch() {
  return useMutation<SearchResponse, Error, SearchRequest>({
    mutationFn: searchDocuments,
  });
}
