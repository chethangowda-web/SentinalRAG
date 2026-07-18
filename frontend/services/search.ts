import { api } from "./api";
import type { SearchRequest, SearchResponse } from "@/types";

export async function searchDocuments(request: SearchRequest): Promise<SearchResponse> {
  const { data } = await api.post<SearchResponse>("/api/v1/search", request);
  return data;
}
