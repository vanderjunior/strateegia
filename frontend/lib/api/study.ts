import { getApiConfig } from "@/lib/api/config";
import { makeApiFailure } from "@/lib/api/errors";
import type {
  ApiResult,
  BackendNextStudySession,
  BackendStudyMaterialSummaryItem,
  StudyMaterialSummaryItemStatus
} from "@/lib/api/types";

const ITEM_STATUSES = new Set<StudyMaterialSummaryItemStatus>([
  "ready",
  "needs_review"
]);

function isAction(value: unknown): value is { label: string; href: string } {
  return (
    Boolean(value) &&
    typeof value === "object" &&
    typeof (value as { label?: unknown }).label === "string" &&
    typeof (value as { href?: unknown }).href === "string"
  );
}

function isSummaryItem(value: unknown): value is BackendStudyMaterialSummaryItem {
  const item = value as Partial<BackendStudyMaterialSummaryItem>;
  return (
    Boolean(value) &&
    typeof value === "object" &&
    typeof item.section_id === "string" &&
    typeof item.title === "string" &&
    typeof item.summary === "string" &&
    Array.isArray(item.key_points) &&
    item.key_points.every((point) => typeof point === "string") &&
    typeof item.estimated_minutes === "number" &&
    Boolean(item.status && ITEM_STATUSES.has(item.status))
  );
}

function isNextStudySessionPayload(value: unknown): value is BackendNextStudySession {
  if (!value || typeof value !== "object") {
    return false;
  }
  const data = value as Partial<BackendNextStudySession>;
  if (data.session_status === "not_ready") {
    return (
      typeof data.message === "string" &&
      Array.isArray(data.next_actions) &&
      data.next_actions.every(isAction) &&
      data.source === "user_scope"
    );
  }
  return (
    (data.session_status === "ready" || data.session_status === "needs_review") &&
    typeof data.session_id === "string" &&
    typeof data.document_id === "string" &&
    typeof data.material_title === "string" &&
    data.material_type === "study_material" &&
    (data.summary_status === "ready" || data.summary_status === "needs_review") &&
    typeof data.estimated_minutes === "number" &&
    typeof data.sections_count === "number" &&
    Array.isArray(data.items) &&
    data.items.every(isSummaryItem) &&
    Array.isArray(data.next_actions) &&
    data.next_actions.every(isAction) &&
    typeof data.message === "string" &&
    data.source === "user_scope"
  );
}

export async function fetchNextStudySession(): Promise<ApiResult<BackendNextStudySession>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: a sessão real não foi consultada.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "A sessão de estudo não está configurada neste ambiente."
    );
  }

  try {
    const response = await fetch("/api/study/session/next", {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível carregar a sessão agora.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "A sessão de estudo não está configurada neste ambiente.",
        503
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Entre para ver sua sessão de estudo.", response.status);
    }
    if (!response.ok) {
      return makeApiFailure(
        "backend",
        "http_error",
        `Backend returned HTTP ${response.status}.`,
        response.status
      );
    }

    try {
      const data = (await response.json()) as BackendNextStudySession;
      if (!isNextStudySessionPayload(data)) {
        return makeApiFailure("backend", "invalid_response", "Não foi possível carregar a sessão agora.", response.status);
      }
      return {
        ok: true,
        data,
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_response", "Não foi possível carregar a sessão agora.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível carregar a sessão agora.");
  }
}
