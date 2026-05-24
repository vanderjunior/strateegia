import { getJson } from "@/lib/api/client";
import type { ApiResult } from "@/lib/api/types";

export interface BackendMaterialPipelineSummary {
  document_id: string;
  current_stage?: string;
  extraction_status?: string;
  metadata_status?: string;
}

export function fetchMaterialPipeline(documentId: string): Promise<ApiResult<BackendMaterialPipelineSummary>> {
  return getJson<BackendMaterialPipelineSummary>(`/api/materials/${documentId}/pipeline`);
}
