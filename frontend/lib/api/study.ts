import { getApiConfig } from "@/lib/api/config";
import { makeApiFailure } from "@/lib/api/errors";
import type {
  ApiResult,
  BackendNextStudySession,
  BackendStudyBlockItem,
  BackendStudyBlockDetail,
  BackendStudyBlocks,
  BackendStudyBlockQuestions,
  BackendStudyMaterialSummaryItem,
  BackendStudyBlockDetailStatus,
  StudyBlockQuestionDifficulty,
  StudyBlockQuestionItemStatus,
  StudyBlockQuestionStatus,
  StudyBlockQuestionType,
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

const BLOCK_DETAIL_STATUSES = new Set<BackendStudyBlockDetailStatus>([
  "ready",
  "needs_review",
  "not_ready"
]);

const QUESTION_STATUSES = new Set<StudyBlockQuestionStatus>([
  "ready",
  "needs_review",
  "not_ready",
  "unsupported"
]);

const QUESTION_TYPES = new Set<StudyBlockQuestionType>([
  "short_answer",
  "true_false",
  "multiple_choice"
]);

const QUESTION_DIFFICULTIES = new Set<StudyBlockQuestionDifficulty>([
  "basic",
  "medium",
  "hard"
]);

const QUESTION_ITEM_STATUSES = new Set<StudyBlockQuestionItemStatus>([
  "candidate",
  "needs_review"
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

function isDetailSummaryStatus(value: unknown): value is BackendStudyBlockDetail["summary_status"] {
  return typeof value === "string" && SUMMARY_STATUSES.has(value) && value !== "failed";
}

function isStudyBlockDetail(value: unknown): value is BackendStudyBlockDetail {
  if (!value || typeof value !== "object") {
    return false;
  }
  const data = value as Partial<BackendStudyBlockDetail>;
  return (
    typeof data.block_id === "string" &&
    Boolean(data.detail_status && BLOCK_DETAIL_STATUSES.has(data.detail_status)) &&
    typeof data.title === "string" &&
    (data.topic_id === null || typeof data.topic_id === "string") &&
    (data.topic_label === null || typeof data.topic_label === "string") &&
    (data.subtopic_id === null || typeof data.subtopic_id === "string") &&
    (data.subtopic_label === null || typeof data.subtopic_label === "string") &&
    typeof data.material_id === "string" &&
    typeof data.material_title === "string" &&
    isDetailSummaryStatus(data.summary_status) &&
    typeof data.estimated_minutes === "number" &&
    Array.isArray(data.sections) &&
    data.sections.every(isSummaryItem) &&
    Array.isArray(data.actions) &&
    data.actions.every(isAction) &&
    data.source === "user_scope"
  );
}

function isQuestionAlternative(value: unknown): value is BackendStudyBlockQuestions["items"][number]["alternatives"][number] {
  const alternative = value as Partial<BackendStudyBlockQuestions["items"][number]["alternatives"][number]>;
  return (
    Boolean(value) &&
    typeof value === "object" &&
    typeof alternative.id === "string" &&
    typeof alternative.text === "string"
  );
}

function isStudyBlockQuestionItem(value: unknown): value is BackendStudyBlockQuestions["items"][number] {
  const item = value as Partial<BackendStudyBlockQuestions["items"][number]>;
  return (
    Boolean(value) &&
    typeof value === "object" &&
    typeof item.question_id === "string" &&
    Boolean(item.type && QUESTION_TYPES.has(item.type)) &&
    typeof item.prompt === "string" &&
    Array.isArray(item.alternatives) &&
    item.alternatives.every(isQuestionAlternative) &&
    (item.topic_label === null || typeof item.topic_label === "string") &&
    (item.subtopic_label === null || typeof item.subtopic_label === "string") &&
    Boolean(item.difficulty && QUESTION_DIFFICULTIES.has(item.difficulty)) &&
    Boolean(item.status && QUESTION_ITEM_STATUSES.has(item.status))
  );
}

function isStudyBlockQuestionsPayload(value: unknown): value is BackendStudyBlockQuestions {
  if (!value || typeof value !== "object") {
    return false;
  }
  const data = value as Partial<BackendStudyBlockQuestions>;
  return (
    typeof data.block_id === "string" &&
    Boolean(data.question_status && QUESTION_STATUSES.has(data.question_status)) &&
    data.mode === "review_only" &&
    Array.isArray(data.items) &&
    data.items.every(isStudyBlockQuestionItem) &&
    typeof data.warnings_count === "number" &&
    data.source === "user_scope"
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

export async function fetchStudyBlockQuestions(blockId: string): Promise<ApiResult<BackendStudyBlockQuestions>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: as questões reais não foram consultadas.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "As questões deste bloco não estão configuradas neste ambiente."
    );
  }

  try {
    const response = await fetch(`/api/study/blocks/${encodeURIComponent(blockId)}/questions`, {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível carregar as questões agora.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "As questões deste bloco não estão configuradas neste ambiente.",
        503
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Entre para ver as questões deste bloco.", response.status);
    }
    if (response.status === 404) {
      return makeApiFailure("backend", "not_found", "Bloco de estudo não encontrado.", response.status);
    }
    if (!response.ok) {
      return makeApiFailure(
        "backend",
        "http_error",
        "Não foi possível carregar as questões agora.",
        response.status
      );
    }

    try {
      const data = (await response.json()) as BackendStudyBlockQuestions;
      if (!isStudyBlockQuestionsPayload(data)) {
        return makeApiFailure("backend", "invalid_response", "Não foi possível carregar as questões agora.", response.status);
      }
      if (data.question_status === "not_ready") {
        return makeApiFailure(
          "backend",
          "not_ready",
          "As questões ainda não estão prontas para este bloco.",
          response.status
        );
      }
      if (data.question_status === "unsupported") {
        return makeApiFailure(
          "unsupported",
          "missing_base_url",
          "As questões deste bloco não estão configuradas neste ambiente.",
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
      return makeApiFailure("backend", "invalid_response", "Não foi possível carregar as questões agora.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível carregar as questões agora.");
  }
}

export async function fetchStudyBlockDetail(blockId: string): Promise<ApiResult<BackendStudyBlockDetail>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: este bloco real não foi consultado.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "Este bloco de estudo não está configurado neste ambiente."
    );
  }

  try {
    const response = await fetch(`/api/study/blocks/${encodeURIComponent(blockId)}`, {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível carregar este bloco agora.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "Este bloco de estudo não está configurado neste ambiente.",
        503
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Entre para ver este bloco de estudo.", response.status);
    }
    if (response.status === 404) {
      return makeApiFailure("backend", "not_found", "Bloco de estudo não encontrado.", response.status);
    }
    if (!response.ok) {
      return makeApiFailure(
        "backend",
        "http_error",
        "Não foi possível carregar este bloco agora.",
        response.status
      );
    }

    try {
      const data = (await response.json()) as BackendStudyBlockDetail;
      if (!isStudyBlockDetail(data)) {
        return makeApiFailure("backend", "invalid_response", "Não foi possível carregar este bloco agora.", response.status);
      }
      if (data.detail_status === "not_ready") {
        return makeApiFailure(
          "backend",
          "not_ready",
          "Este bloco ainda não está pronto para estudo.",
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
      return makeApiFailure("backend", "invalid_response", "Não foi possível carregar este bloco agora.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível carregar este bloco agora.");
  }
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
