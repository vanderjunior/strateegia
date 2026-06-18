import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type {
  AdaptiveQuestionQueueStatus,
  BackendAdaptiveQuestionQueue,
  BackendStudyBlockQuestionAlternative,
  BackendStudyBlockQuestionItem,
  StudyBlockQuestionDifficulty,
  StudyBlockQuestionItemStatus,
  StudyBlockQuestionType
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_QUEUE_STATUSES = new Set<AdaptiveQuestionQueueStatus>([
  "ready",
  "needs_review",
  "not_ready"
]);

const ALLOWED_QUESTION_TYPES = new Set<StudyBlockQuestionType>([
  "short_answer",
  "true_false",
  "multiple_choice"
]);

const ALLOWED_DIFFICULTIES = new Set<StudyBlockQuestionDifficulty>([
  "basic",
  "medium",
  "hard"
]);

const ALLOWED_ITEM_STATUSES = new Set<StudyBlockQuestionItemStatus>([
  "candidate",
  "needs_review"
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
  "priority",
  "bucket",
  "mastery",
  "raw text",
  "raw_text",
  marker("extracted", "_", "text"),
  "chunks",
  "chunk body",
  "section body",
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

function toSafeQueueStatus(value: unknown): AdaptiveQuestionQueueStatus {
  return typeof value === "string" && ALLOWED_QUEUE_STATUSES.has(value as AdaptiveQuestionQueueStatus)
    ? (value as AdaptiveQuestionQueueStatus)
    : "not_ready";
}

function toSafeQuestionType(value: unknown): StudyBlockQuestionType {
  return typeof value === "string" && ALLOWED_QUESTION_TYPES.has(value as StudyBlockQuestionType)
    ? (value as StudyBlockQuestionType)
    : "short_answer";
}

function toSafeDifficulty(value: unknown): StudyBlockQuestionDifficulty {
  return typeof value === "string" && ALLOWED_DIFFICULTIES.has(value as StudyBlockQuestionDifficulty)
    ? (value as StudyBlockQuestionDifficulty)
    : "basic";
}

function toSafeItemStatus(value: unknown): StudyBlockQuestionItemStatus {
  return typeof value === "string" && ALLOWED_ITEM_STATUSES.has(value as StudyBlockQuestionItemStatus)
    ? (value as StudyBlockQuestionItemStatus)
    : "needs_review";
}

function sanitizeAlternative(value: unknown): BackendStudyBlockQuestionAlternative | null {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const id = toSafeString(raw.id);
  const text = toSafeString(raw.text);
  if (!id || !text) {
    return null;
  }
  return { id, text };
}

function sanitizeAlternatives(value: unknown): BackendStudyBlockQuestionAlternative[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map(sanitizeAlternative)
    .filter((item): item is BackendStudyBlockQuestionAlternative => item !== null)
    .slice(0, 6);
}

function sanitizeQuestionItem(value: unknown): BackendStudyBlockQuestionItem | null {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const questionId = toSafeString(raw.question_id);
  const prompt = toSafeString(raw.prompt);
  if (!questionId || !prompt) {
    return null;
  }
  return {
    question_id: questionId,
    type: toSafeQuestionType(raw.type),
    prompt,
    alternatives: sanitizeAlternatives(raw.alternatives),
    topic_label: toSafeNullableString(raw.topic_label),
    subtopic_label: toSafeNullableString(raw.subtopic_label),
    difficulty: toSafeDifficulty(raw.difficulty),
    status: toSafeItemStatus(raw.status)
  };
}

function sanitizeQuestionItems(value: unknown): BackendStudyBlockQuestionItem[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map(sanitizeQuestionItem)
    .filter((item): item is BackendStudyBlockQuestionItem => item !== null)
    .slice(0, 10);
}

function sanitizeAdaptiveQuestionQueue(payload: unknown): BackendAdaptiveQuestionQueue {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const queueStatus = toSafeQueueStatus(raw.queue_status);
  const items = queueStatus === "not_ready" ? [] : sanitizeQuestionItems(raw.items);
  return {
    block_id: toSafeString(raw.block_id),
    queue_status: queueStatus,
    mode: "attempt_aware",
    items_count: items.length,
    items,
    source: "user_scope"
  };
}

function parseLimit(request: Request): number | null {
  const rawLimit = new URL(request.url).searchParams.get("limit") ?? "5";
  if (!/^\d+$/.test(rawLimit)) {
    return null;
  }
  const limit = Number.parseInt(rawLimit, 10);
  return limit >= 1 && limit <= 10 ? limit : null;
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ blockId: string }> }
) {
  const baseUrl = getServerBackendBaseUrl();
  const limit = parseLimit(request);
  const { blockId } = await params;
  const decodedBlockId = decodeRouteParam(blockId);

  if (limit === null) {
    return NextResponse.json(
      { detail: "Não foi possível carregar as questões agora." },
      { status: 422 }
    );
  }

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "As questões deste bloco não estão configuradas neste ambiente." },
      { status: 503 }
    );
  }

  try {
    const backendResponse = await fetch(
      `${baseUrl}/api/study/blocks/${encodeURIComponent(decodedBlockId)}/questions/next?limit=${limit}`,
      {
        method: "GET",
        headers: request.headers.get("cookie")
          ? {
              cookie: request.headers.get("cookie") as string
            }
          : undefined,
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
    return NextResponse.json(sanitizeAdaptiveQuestionQueue(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível carregar as questões agora." },
      { status: 502 }
    );
  }
}
