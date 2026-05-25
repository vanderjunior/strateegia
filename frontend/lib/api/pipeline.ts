import { getJson } from "@/lib/api/client";
import type {
  ApiResult,
  BackendDocumentChunk,
  BackendDocumentPipelineState,
  BackendDocumentSection
} from "@/lib/api/types";

export function fetchMaterialPipelineState(
  documentId: string
): Promise<ApiResult<BackendDocumentPipelineState>> {
  return getJson<BackendDocumentPipelineState>(`/api/materials/${documentId}/pipeline`);
}

export function fetchMaterialSections(
  documentId: string
): Promise<ApiResult<BackendDocumentSection[]>> {
  return getJson<BackendDocumentSection[]>(`/api/materials/${documentId}/sections`);
}

export function fetchMaterialChunks(documentId: string): Promise<ApiResult<BackendDocumentChunk[]>> {
  return getJson<BackendDocumentChunk[]>(`/api/materials/${documentId}/chunks`);
}
