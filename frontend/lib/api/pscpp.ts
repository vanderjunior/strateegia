import { getJson } from "@/lib/api/client";
import type { ApiResult, BackendExamProfile } from "@/lib/api/types";

export const PSCPP_EXAM_PROFILE_ID = "exam-profile:marinha-pscpp";

export function fetchExamProfiles(): Promise<ApiResult<BackendExamProfile[]>> {
  return getJson<BackendExamProfile[]>("/api/exam-profiles");
}

export function fetchPscppExamProfile(): Promise<ApiResult<BackendExamProfile>> {
  return getJson<BackendExamProfile>(`/api/exam-profiles/${PSCPP_EXAM_PROFILE_ID}`);
}
