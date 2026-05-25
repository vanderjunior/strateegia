import { getJson } from "@/lib/api/client";
import type { ApiResult, BackendDocumentSummary } from "@/lib/api/types";

export function fetchDocuments(): Promise<ApiResult<BackendDocumentSummary[]>> {
  return getJson<BackendDocumentSummary[]>("/api/documents");
}

export function fetchDocumentById(documentId: string): Promise<ApiResult<BackendDocumentSummary>> {
  return getJson<BackendDocumentSummary>(`/api/documents/${documentId}`);
}
