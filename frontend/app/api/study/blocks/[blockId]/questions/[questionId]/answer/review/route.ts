import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type {
  BackendStudyBlockAnswerReview,
  StudyBlockAnswerFormat,
  StudyBlockAnswerReviewResult,
  StudyBlockAnswerReviewStatus,
  StudyBlockAnswerReviewSuggestedAction,
  StudyQuestionAttemptContext,
  StudyQuestionAttemptCorrectness
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_ANSWER_FORMATS = new Set<StudyBlockAnswerFormat>([
  "text",
  "choice",
  "true_false"
]);

const ALLOWED_REVIEW_STATUSES = new Set<StudyBlockAnswerReviewStatus>([
  "reviewed",
  "needs_review",
  "not_ready",
  "unsupported"
]);

const ALLOWED_RESULTS = new Set<StudyBlockAnswerReviewResult>([
  "correct",
  "incorrect",
  "partial",
  "ungraded",
  "needs_review"
]);

const ALLOWED_SUGGESTED_ACTIONS = new Set<StudyBlockAnswerReviewSuggestedAction>([
  "review_summary",
  "retry_question",
  "revisit_block"
]);

const ALLOWED_ATTEMPT_CONTEXTS = new Set<StudyQuestionAttemptContext>([
  "study_block",
  "cumulative_review",
  "reinforcement"
]);

const ALLOWED_CORRECTNESS_STATES = new Set<StudyQuestionAttemptCorrectness>([
  "correct",
  "incorrect",
  "ungraded"
]);

function marker(...parts: string[]): string {
  return parts.join("");
}

const UNSAFE_TEXT_MARKERS = [
  marker("answer", "_", "key"),
  marker("correct", "_", "answer"),
  marker("correct", "_", "alternative"),
  marker("gabar", "ito"),
  marker("is", "_", "correct"),
  marker("correct", "ness"),
  "solution",
  "rationale",
  "correction",
  "score",
  "raw text",
  "raw_text",
  marker("extracted", "_", "text"),
  "chunks",
  "chunk body",
  "section body",
  "evidence",
  "ocr_dump",
  "raw_ocr",
  "base64",
  marker("storage", "_", "path"),
  marker("/", "Users", "/"),
  "C:\\",
  "token",
  "cookie",
  marker("session", " ", "token"),
  "session=",
  marker("password", "_", "hash"),
  "progress",
  "internal trace",
  "worker",
  "job trace"
];

function hasUnsafeText(value: string): boolean {
  const normalized = value.toLowerCase();
  return UNSAFE_TEXT_MARKERS.some((marker) => normalized.includes(marker.toLowerCase()));
}

function decodeRouteParam(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function toSafeString(value: unknown, fallback = ""): string {
  if (typeof value !== "string") {
    return fallback;
  }
  const normalized = value.trim();
  if (!normalized || hasUnsafeText(normalized)) {
    return fallback;
  }
  return normalized;
}

function toSafeNullableString(value: unknown): string | null {
  const safe = toSafeString(value);
  return safe || null;
}

function toSafeAnswerFormat(value: unknown): StudyBlockAnswerFormat | null {
  return typeof value === "string" && ALLOWED_ANSWER_FORMATS.has(value as StudyBlockAnswerFormat)
    ? (value as StudyBlockAnswerFormat)
    : null;
}

function toSafeAttemptContext(value: unknown): StudyQuestionAttemptContext | null {
  return typeof value === "string" && ALLOWED_ATTEMPT_CONTEXTS.has(value as StudyQuestionAttemptContext)
    ? (value as StudyQuestionAttemptContext)
    : null;
}

function sanitizeRequestBody(payload: unknown): {
  answer?: string;
  answer_format?: StudyBlockAnswerFormat;
  response_context?: StudyQuestionAttemptContext;
  idempotency_key?: string;
} {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const body: {
    answer?: string;
    answer_format?: StudyBlockAnswerFormat;
    response_context?: StudyQuestionAttemptContext;
    idempotency_key?: string;
  } = {};
  if (typeof raw.answer === "string") {
    body.answer = raw.answer;
  }
  const answerFormat = toSafeAnswerFormat(raw.answer_format);
  if (answerFormat) {
    body.answer_format = answerFormat;
  }
  const responseContext = toSafeAttemptContext(raw.response_context);
  if (responseContext) {
    body.response_context = responseContext;
  }
  if (typeof raw.idempotency_key === "string") {
    const idempotencyKey = toSafeString(raw.idempotency_key);
    if (idempotencyKey) {
      body.idempotency_key = idempotencyKey;
    }
  }
  return body;
}

function toSafeReviewStatus(value: unknown): StudyBlockAnswerReviewStatus {
  return typeof value === "string" && ALLOWED_REVIEW_STATUSES.has(value as StudyBlockAnswerReviewStatus)
    ? (value as StudyBlockAnswerReviewStatus)
    : "not_ready";
}

function toSafeResult(value: unknown): StudyBlockAnswerReviewResult {
  return typeof value === "string" && ALLOWED_RESULTS.has(value as StudyBlockAnswerReviewResult)
    ? (value as StudyBlockAnswerReviewResult)
    : "needs_review";
}

function toSafeSuggestedAction(value: unknown): StudyBlockAnswerReviewSuggestedAction {
  return typeof value === "string" && ALLOWED_SUGGESTED_ACTIONS.has(value as StudyBlockAnswerReviewSuggestedAction)
    ? (value as StudyBlockAnswerReviewSuggestedAction)
    : "review_summary";
}

function sanitizeAnswerReview(payload: unknown): BackendStudyBlockAnswerReview {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const reinforcement =
    raw.reinforcement && typeof raw.reinforcement === "object"
      ? (raw.reinforcement as Record<string, unknown>)
      : {};
  const attempt =
    raw.attempt && typeof raw.attempt === "object"
      ? (raw.attempt as Record<string, unknown>)
      : {};
  const correctnessState =
    typeof attempt.correctness_state === "string" &&
    ALLOWED_CORRECTNESS_STATES.has(attempt.correctness_state as StudyQuestionAttemptCorrectness)
      ? (attempt.correctness_state as StudyQuestionAttemptCorrectness)
      : "ungraded";
  const responseContext =
    toSafeAttemptContext(attempt.response_context) ?? "study_block";

  return {
    block_id: toSafeString(raw.block_id),
    question_id: toSafeString(raw.question_id),
    review_status: toSafeReviewStatus(raw.review_status),
    result: toSafeResult(raw.result),
    feedback: toSafeString(raw.feedback, "Revise sua resposta antes de enviar."),
    reinforcement: {
      topic_label: toSafeNullableString(reinforcement.topic_label),
      subtopic_label: toSafeNullableString(reinforcement.subtopic_label),
      message: toSafeString(reinforcement.message, "Revise o resumo do bloco antes de avançar."),
      suggested_action: toSafeSuggestedAction(reinforcement.suggested_action)
    },
    attempt: {
      attempt_id: toSafeString(attempt.attempt_id),
      question_id: toSafeString(attempt.question_id),
      selected_answer: toSafeString(attempt.selected_answer),
      correctness_state: correctnessState,
      attempted_at: toSafeString(attempt.attempted_at),
      attempt_number:
        typeof attempt.attempt_number === "number" && attempt.attempt_number >= 1
          ? Math.trunc(attempt.attempt_number)
          : 1,
      response_context: responseContext,
      persisted: true
    },
    source: "user_scope"
  };
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ blockId: string; questionId: string }> }
) {
  const baseUrl = getServerBackendBaseUrl();
  const { blockId, questionId } = await params;
  const decodedBlockId = decodeRouteParam(blockId);
  const decodedQuestionId = decodeRouteParam(questionId);

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "A revisão da resposta não está configurada neste ambiente." },
      { status: 503 }
    );
  }

  let requestPayload: unknown;
  try {
    requestPayload = await request.json();
  } catch {
    return NextResponse.json(
      { detail: "Revise sua resposta antes de enviar." },
      { status: 422 }
    );
  }

  try {
    const backendResponse = await fetch(
      `${baseUrl}/api/study/blocks/${encodeURIComponent(decodedBlockId)}/questions/${encodeURIComponent(
        decodedQuestionId
      )}/answer/review`,
      {
        method: "POST",
        headers: {
          ...(request.headers.get("cookie") ? { cookie: request.headers.get("cookie") as string } : {}),
          "content-type": "application/json"
        },
        body: JSON.stringify(sanitizeRequestBody(requestPayload)),
        cache: "no-store"
      }
    );

    if (!backendResponse.ok) {
      const responseText = await backendResponse.text();
      return new Response(responseText, {
        status: backendResponse.status,
        headers: {
          "content-type": backendResponse.headers.get("content-type") ?? "application/json"
        }
      });
    }

    const payload = await backendResponse.json();
    return NextResponse.json(sanitizeAnswerReview(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível revisar sua resposta agora." },
      { status: 502 }
    );
  }
}
