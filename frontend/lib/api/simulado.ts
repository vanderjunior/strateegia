import { getJson } from "@/lib/api/client";
import type { ApiResult } from "@/lib/api/types";

export interface BackendSimuladoBlueprintSummary {
  blueprint_id?: string;
  readiness_state?: string;
  question_slot_count?: number;
}

export function fetchSimuladoBlueprint(blueprintId: string): Promise<ApiResult<BackendSimuladoBlueprintSummary>> {
  return getJson<BackendSimuladoBlueprintSummary>(`/api/simulado-blueprint/${blueprintId}`);
}
