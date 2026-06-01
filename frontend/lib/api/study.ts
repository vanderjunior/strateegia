import { getApiConfig } from "@/lib/api/config";
import { makeApiFailure } from "@/lib/api/errors";
import type {
  ApiResult,
  BackendNextStudySession,
  BackendStudyBlockItem,
  BackendStudyBlocks,
  BackendStudyMaterialSummaryItem,
  StudyBlockItemStatus,
  StudyBlocksScopeStatus,
  StudyBlocksStatus,
  StudyMaterialSummaryItemStatus
} from "@/lib/api/types";

const BLOCK_STATUSES = new Set<StudyBlocksStatus>([
  "ready",
  "partial",
  "not_ready",
  "needs_review"
]);

const SCOPE_STATUSES = new Set<StudyBlocksScopeStatus>([
  "connected_to_edital",
  "material_only",
  "not_ready"
]);

const BLOCK_ITEM_STATUSES = new Set<StudyBlockItemStatus>([
  "ready",
  "needs_review",
  "not_ready"
]);

const SUMMARY_STATUSES = new Set([
  "ready",
  "needs_review",
  "not_ready",
  "failed"
]);

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

function isStudyBlockItem(value: unknown): value is BackendStudyBlockItem {
  const item = value as Partial<BackendStudyBlockItem>;
  return (
    Boolean(value) &&
    typeof value === "object" &&
    typeof item.block_id === "string" &&
    typeof item.title === "string" &&
    (item.topic_id === null || typeof item.topic_id === "string") &&
    (item.topic_label === null || typeof item.topic_label === "string") &&
    (item.subtopic_id === null || typeof item.subtopic_id === "string") &&
    (item.subtopic_label === null || typeof item.subtopic_label === "string") &&
    typeof item.material_id === "string" &&
    typeof item.material_title === "string" &&
    typeof item.sections_count === "number" &&
    Boolean(item.summary_status && SUMMARY_STATUSES.has(item.summary_status)) &&
    typeof item.estimated_minutes === "number" &&
    Boolean(item.status && BLOCK_ITEM_STATUSES.has(item.status)) &&
    Array.isArray(item.actions) &&
    item.actions.every(isAction)
  );
}

function isStudyBlocksPayload(value: unknown): value is BackendStudyBlocks {
  if (!value || typeof value !== "object") {
    return false;
  }
  const data = value as Partial<BackendStudyBlocks>;
  return (
    Boolean(data.blocks_status && BLOCK_STATUSES.has(data.blocks_status)) &&
    Boolean(data.scope_status && SCOPE_STATUSES.has(data.scope_status)) &&
    typeof data.blocks_count === "number" &&
    typeof data.estimated_minutes === "number" &&
    Array.isArray(data.items) &&
    data.items.every(isStudyBlockItem) &&
    (data.message === undefined || typeof data.message === "string") &&
    data.source === "user_scope"
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

export async function fetchStudyBlocks(): Promise<ApiResult<BackendStudyBlocks>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: os blocos reais não foram consultados.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "Os blocos de estudo não estão configurados neste ambiente."
    );
  }

  try {
    const response = await fetch("/api/study/blocks", {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível carregar seus blocos agora.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "Os blocos de estudo não estão configurados neste ambiente.",
        503
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Entre para ver seus blocos de estudo.", response.status);
    }
    if (!response.ok) {
      return makeApiFailure(
        "backend",
        "http_error",
        "Não foi possível carregar seus blocos agora.",
        response.status
      );
    }

    try {
      const data = (await response.json()) as BackendStudyBlocks;
      if (!isStudyBlocksPayload(data)) {
        return makeApiFailure("backend", "invalid_response", "Não foi possível carregar seus blocos agora.", response.status);
      }
      if (data.blocks_status === "not_ready") {
        return makeApiFailure(
          "backend",
          "not_ready",
          data.message || "Envie e prepare um material de estudo para montar seus blocos.",
          response.status
        );
      }
      return {
        ok: true,
        data,
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_response", "Não foi possível carregar seus blocos agora.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível carregar seus blocos agora.");
  }
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
