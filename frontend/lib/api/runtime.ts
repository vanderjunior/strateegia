import { getJson } from "@/lib/api/client";
import type { ApiResult, BackendDashboardOverview } from "@/lib/api/types";

export function fetchDashboardOverview(): Promise<ApiResult<BackendDashboardOverview>> {
  return getJson<BackendDashboardOverview>("/api/dashboard/overview");
}
