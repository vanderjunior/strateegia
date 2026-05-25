import { getJson } from "@/lib/api/client";
import type {
  ApiResult,
  BackendBibliographyAlignment,
  BackendEditalExtraction
} from "@/lib/api/types";

export function fetchEditalById(editalId: string): Promise<ApiResult<BackendEditalExtraction>> {
  return getJson<BackendEditalExtraction>(`/api/edital/${editalId}`);
}

export function fetchEditalAlignment(editalId: string): Promise<ApiResult<BackendBibliographyAlignment>> {
  return getJson<BackendBibliographyAlignment>(`/api/edital/${editalId}/alignment`);
}
