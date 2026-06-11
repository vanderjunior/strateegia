import { getApiConfig } from "@/lib/api/config";
import { makeApiFailure } from "@/lib/api/errors";
import type {
  ApiResult,
  BackendNextStudySession,
  BackendNextReviewBlock,
  BackendStudyBlockItem,
  BackendStudyBlockAnswerReview,
  BackendStudyBlockDetail,
  BackendStudyBlocks,
  BackendStudyBlockQuestions,
  StudyProgressEventRequest,
  StudyProgressEventResponse,
  StudyProgressEventResult,
  StudyProgressEventType,
  StudyProgressReviewBasis,
  StudyProgressStatus,
  StudyProgressSummary,
  StudyProgressSummaryResult,
  StudyProgressTargetType,
  BackendStudyMaterialSummaryItem,
  BackendStudyBlockDetailStatus,
  StudyBlockAnswerFormat,
  StudyBlockAnswerReviewResult,
  StudyBlockAnswerReviewStatus,
  StudyBlockAnswerReviewSuggestedAction,
  StudyBlockQuestionDifficulty,
  StudyBlockQuestionItemStatus,
  StudyBlockQuestionStatus,
  StudyBlockQuestionType,
  StudyBlockItemStatus,
  ReviewBlockBasis,
  ReviewBlockSectionStatus,
  ReviewBlockStatus,
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

const REVIEW_STATUSES = new Set<ReviewBlockStatus>([
  "ready",
  "partial",
  "not_ready",
  "needs_review"
]);

const REVIEW_BASES = new Set<ReviewBlockBasis>([
  "prepared_materials",
  "study_blocks"
]);

const REVIEW_SECTION_STATUSES = new Set<ReviewBlockSectionStatus>([
  "ready",
  "needs_review",
  "not_ready"
]);

const PROGRESS_EVENT_TYPES = new Set<StudyProgressEventType>([
  "block_opened",
  "block_marked_studied",
  "question_reviewed",
  "review_opened",
  "review_completed"
]);

const PROGRESS_TARGET_TYPES = new Set<StudyProgressTargetType>([
  "block",
  "question",
  "review",
  "material"
]);

const PROGRESS_STATUSES = new Set<StudyProgressStatus>([
  "ready",
  "not_ready"
]);

const PROGRESS_REVIEW_BASES = new Set<StudyProgressReviewBasis>([
  "prepared_materials",
  "studied_materials",
  "none"
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

const ANSWER_FORMATS = new Set<StudyBlockAnswerFormat>([
  "text",
  "choice",
  "true_false"
]);

const ANSWER_REVIEW_STATUSES = new Set<StudyBlockAnswerReviewStatus>([
  "reviewed",
  "needs_review",
  "not_ready",
  "unsupported"
]);

const ANSWER_REVIEW_RESULTS = new Set<StudyBlockAnswerReviewResult>([
  "correct",
  "incorrect",
  "partial",
  "ungraded",
  "needs_review"
]);

const ANSWER_REVIEW_ACTIONS = new Set<StudyBlockAnswerReviewSuggestedAction>([
  "review_summary",
  "retry_question",
  "revisit_block"
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

function isReviewSummaryItem(value: unknown): value is BackendNextReviewBlock["summary"]["items"][number] {
  const item = value as Partial<BackendNextReviewBlock["summary"]["items"][number]>;
  return (
    Boolean(value) &&
    typeof value === "object" &&
    typeof item.title === "string" &&
    typeof item.message === "string" &&
    (item.topic_label === null || typeof item.topic_label === "string") &&
    (item.subtopic_label === null || typeof item.subtopic_label === "string")
  );
}

function isReviewReinforcementItem(
  value: unknown
): value is BackendNextReviewBlock["reinforcement"]["items"][number] {
  const item = value as Partial<BackendNextReviewBlock["reinforcement"]["items"][number]>;
  return (
    Boolean(value) &&
    typeof value === "object" &&
    (item.topic_label === null || typeof item.topic_label === "string") &&
    (item.subtopic_label === null || typeof item.subtopic_label === "string") &&
    typeof item.message === "string"
  );
}

function isReviewSectionStatus(value: unknown): value is ReviewBlockSectionStatus {
  return typeof value === "string" && REVIEW_SECTION_STATUSES.has(value as ReviewBlockSectionStatus);
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

function isStudyBlockAnswerReviewPayload(value: unknown): value is BackendStudyBlockAnswerReview {
  if (!value || typeof value !== "object") {
    return false;
  }
  const data = value as Partial<BackendStudyBlockAnswerReview>;
  const reinforcement = data.reinforcement as Partial<BackendStudyBlockAnswerReview["reinforcement"]> | undefined;
  return (
    typeof data.block_id === "string" &&
    typeof data.question_id === "string" &&
    Boolean(data.review_status && ANSWER_REVIEW_STATUSES.has(data.review_status)) &&
    Boolean(data.result && ANSWER_REVIEW_RESULTS.has(data.result)) &&
    typeof data.feedback === "string" &&
    Boolean(reinforcement) &&
    typeof reinforcement === "object" &&
    (reinforcement.topic_label === null || typeof reinforcement.topic_label === "string") &&
    (reinforcement.subtopic_label === null || typeof reinforcement.subtopic_label === "string") &&
    typeof reinforcement.message === "string" &&
    Boolean(reinforcement.suggested_action && ANSWER_REVIEW_ACTIONS.has(reinforcement.suggested_action)) &&
    data.source === "user_scope"
  );
}

function normalizeStudyBlockAnswerReviewPayload(data: BackendStudyBlockAnswerReview): BackendStudyBlockAnswerReview {
  return {
    block_id: data.block_id,
    question_id: data.question_id,
    review_status: data.review_status,
    result: data.result,
    feedback: data.feedback,
    reinforcement: {
      topic_label: data.reinforcement.topic_label,
      subtopic_label: data.reinforcement.subtopic_label,
      message: data.reinforcement.message,
      suggested_action: data.reinforcement.suggested_action
    },
    source: "user_scope"
  };
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

function isNextReviewBlockPayload(value: unknown): value is BackendNextReviewBlock {
  if (!value || typeof value !== "object") {
    return false;
  }
  const data = value as Partial<BackendNextReviewBlock>;
  const summary = data.summary as Partial<BackendNextReviewBlock["summary"]> | undefined;
  const questions = data.questions as Partial<BackendNextReviewBlock["questions"]> | undefined;
  const reinforcement = data.reinforcement as Partial<BackendNextReviewBlock["reinforcement"]> | undefined;
  return (
    Boolean(data.review_status && REVIEW_STATUSES.has(data.review_status)) &&
    (data.review_id === null || typeof data.review_id === "string") &&
    Boolean(data.basis && REVIEW_BASES.has(data.basis)) &&
    typeof data.materials_count === "number" &&
    typeof data.blocks_count === "number" &&
    typeof data.estimated_minutes === "number" &&
    typeof data.title === "string" &&
    Boolean(summary) &&
    typeof summary === "object" &&
    isReviewSectionStatus(summary.status) &&
    Array.isArray(summary.items) &&
    summary.items.every(isReviewSummaryItem) &&
    Boolean(questions) &&
    typeof questions === "object" &&
    isReviewSectionStatus(questions.status) &&
    typeof questions.items_count === "number" &&
    Boolean(reinforcement) &&
    typeof reinforcement === "object" &&
    isReviewSectionStatus(reinforcement.status) &&
    typeof reinforcement.weak_topics_count === "number" &&
    Array.isArray(reinforcement.items) &&
    reinforcement.items.every(isReviewReinforcementItem) &&
    Array.isArray(data.actions) &&
    data.actions.every(isAction) &&
    (data.message === undefined || typeof data.message === "string") &&
    data.source === "user_scope"
  );
}

function isStudyProgressEventPayload(value: unknown): value is StudyProgressEventResponse {
  if (!value || typeof value !== "object") {
    return false;
  }
  const data = value as Partial<StudyProgressEventResponse>;
  return (
    typeof data.event_id === "string" &&
    Boolean(data.event_type && PROGRESS_EVENT_TYPES.has(data.event_type)) &&
    Boolean(data.target_type && PROGRESS_TARGET_TYPES.has(data.target_type)) &&
    typeof data.target_id === "string" &&
    typeof data.created_at === "string" &&
    data.source === "user_scope"
  );
}

function normalizeStudyProgressEventPayload(data: StudyProgressEventResponse): StudyProgressEventResponse {
  return {
    event_id: data.event_id,
    event_type: data.event_type,
    target_type: data.target_type,
    target_id: data.target_id,
    created_at: data.created_at,
    source: "user_scope"
  };
}

function isStudyProgressSummaryPayload(value: unknown): value is StudyProgressSummary {
  if (!value || typeof value !== "object") {
    return false;
  }
  const data = value as Partial<StudyProgressSummary>;
  return (
    Boolean(data.progress_status && PROGRESS_STATUSES.has(data.progress_status)) &&
    typeof data.opened_blocks_count === "number" &&
    typeof data.studied_blocks_count === "number" &&
    typeof data.prepared_materials_count === "number" &&
    typeof data.studied_materials_count === "number" &&
    typeof data.review_due === "boolean" &&
    Boolean(data.review_basis && PROGRESS_REVIEW_BASES.has(data.review_basis)) &&
    typeof data.reviewed_questions_count === "number" &&
    typeof data.weak_topics_count === "number" &&
    data.source === "user_scope"
  );
}

function normalizeStudyProgressSummaryPayload(data: StudyProgressSummary): StudyProgressSummary {
  return {
    progress_status: data.progress_status,
    opened_blocks_count: data.opened_blocks_count,
    studied_blocks_count: data.studied_blocks_count,
    prepared_materials_count: data.prepared_materials_count,
    studied_materials_count: data.studied_materials_count,
    review_due: data.review_due,
    review_basis: data.review_basis,
    reviewed_questions_count: data.reviewed_questions_count,
    weak_topics_count: data.weak_topics_count,
    source: "user_scope"
  };
}

export async function createStudyProgressEvent(
  input: StudyProgressEventRequest
): Promise<StudyProgressEventResult> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: o progresso real não foi registrado.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "O registro de progresso não está configurado neste ambiente."
    );
  }

  try {
    const response = await fetch("/api/study/progress/events", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json"
      },
      credentials: "include",
      cache: "no-store",
      body: JSON.stringify({
        event_type: input.event_type,
        target_type: input.target_type,
        target_id: input.target_id,
        idempotency_key: input.idempotency_key ?? null
      })
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível registrar esta ação agora.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "O registro de progresso não está configurado neste ambiente.",
        503
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Entre para acompanhar seu progresso.", response.status);
    }
    if (response.status === 422) {
      return makeApiFailure(
        "backend",
        "invalid_request",
        "Não foi possível registrar este bloco.",
        response.status
      );
    }
    if (!response.ok) {
      return makeApiFailure(
        "backend",
        "http_error",
        "Não foi possível registrar esta ação agora.",
        response.status
      );
    }

    try {
      const data = (await response.json()) as StudyProgressEventResponse;
      if (!isStudyProgressEventPayload(data)) {
        return makeApiFailure(
          "backend",
          "invalid_response",
          "Não foi possível registrar esta ação agora.",
          response.status
        );
      }
      return {
        ok: true,
        data: normalizeStudyProgressEventPayload(data),
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure(
        "backend",
        "invalid_response",
        "Não foi possível registrar esta ação agora.",
        response.status
      );
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível registrar esta ação agora.");
  }
}

export async function fetchStudyProgressSummary(): Promise<StudyProgressSummaryResult> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: o progresso real não foi consultado.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "O resumo de progresso não está configurado neste ambiente."
    );
  }

  try {
    const response = await fetch("/api/study/progress/summary", {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure(
        "offline",
        "backend_offline",
        "Não foi possível carregar seu resumo de progresso agora.",
        502
      );
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "O resumo de progresso não está configurado neste ambiente.",
        503
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Entre para acompanhar seu progresso.", response.status);
    }
    if (!response.ok) {
      return makeApiFailure(
        "backend",
        "http_error",
        "Não foi possível carregar seu resumo de progresso agora.",
        response.status
      );
    }

    try {
      const data = (await response.json()) as StudyProgressSummary;
      if (!isStudyProgressSummaryPayload(data)) {
        return makeApiFailure(
          "backend",
          "invalid_response",
          "Não foi possível carregar seu resumo de progresso agora.",
          response.status
        );
      }
      return {
        ok: true,
        data: normalizeStudyProgressSummaryPayload(data),
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure(
        "backend",
        "invalid_response",
        "Não foi possível carregar seu resumo de progresso agora.",
        response.status
      );
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível carregar seu resumo de progresso agora.");
  }
}

export async function fetchNextReviewBlock(): Promise<ApiResult<BackendNextReviewBlock>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: a revisão real não foi consultada.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "A revisão acumulada não está configurada neste ambiente."
    );
  }

  try {
    const response = await fetch("/api/study/review/next", {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível carregar a revisão agora.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "A revisão acumulada não está configurada neste ambiente.",
        503
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Entre para ver sua revisão acumulada.", response.status);
    }
    if (!response.ok) {
      return makeApiFailure(
        "backend",
        "http_error",
        "Não foi possível carregar a revisão agora.",
        response.status
      );
    }

    try {
      const data = (await response.json()) as BackendNextReviewBlock;
      if (!isNextReviewBlockPayload(data)) {
        return makeApiFailure("backend", "invalid_response", "Não foi possível carregar a revisão agora.", response.status);
      }
      if (data.review_status === "not_ready") {
        return makeApiFailure(
          "backend",
          "not_ready",
          data.message || "Prepare pelo menos 3 materiais de estudo para montar uma revisão acumulada.",
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
      return makeApiFailure("backend", "invalid_response", "Não foi possível carregar a revisão agora.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível carregar a revisão agora.");
  }
}

export async function reviewStudyBlockQuestionAnswer(
  blockId: string,
  questionId: string,
  payload: {
    answer: string;
    answer_format: StudyBlockAnswerFormat;
  }
): Promise<ApiResult<BackendStudyBlockAnswerReview>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: a resposta real não foi revisada.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "A revisão da resposta não está configurada neste ambiente."
    );
  }

  if (!ANSWER_FORMATS.has(payload.answer_format)) {
    return makeApiFailure("backend", "validation_error", "Revise sua resposta antes de enviar.", 422);
  }

  try {
    const response = await fetch(
      `/api/study/blocks/${encodeURIComponent(blockId)}/questions/${encodeURIComponent(questionId)}/answer/review`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json"
        },
        credentials: "include",
        cache: "no-store",
        body: JSON.stringify({
          answer: payload.answer,
          answer_format: payload.answer_format
        })
      }
    );

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível revisar sua resposta agora.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "A revisão da resposta não está configurada neste ambiente.",
        503
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Entre para revisar sua resposta.", response.status);
    }
    if (response.status === 404) {
      return makeApiFailure("backend", "not_found", "Questão ou bloco de estudo não encontrado.", response.status);
    }
    if (response.status === 422) {
      return makeApiFailure("backend", "validation_error", "Revise sua resposta antes de enviar.", response.status);
    }
    if (!response.ok) {
      return makeApiFailure(
        "backend",
        "http_error",
        "Não foi possível revisar sua resposta agora.",
        response.status
      );
    }

    try {
      const data = (await response.json()) as BackendStudyBlockAnswerReview;
      if (!isStudyBlockAnswerReviewPayload(data)) {
        return makeApiFailure("backend", "invalid_response", "Não foi possível revisar sua resposta agora.", response.status);
      }
      if (data.review_status === "not_ready") {
        return makeApiFailure("backend", "not_ready", "Não foi possível revisar sua resposta agora.", response.status);
      }
      if (data.review_status === "unsupported") {
        return makeApiFailure(
          "unsupported",
          "missing_base_url",
          "A revisão da resposta não está configurada neste ambiente.",
          response.status
        );
      }
      return {
        ok: true,
        data: normalizeStudyBlockAnswerReviewPayload(data),
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_response", "Não foi possível revisar sua resposta agora.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível revisar sua resposta agora.");
  }
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
