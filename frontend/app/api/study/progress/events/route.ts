import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type {
  StudyProgressEventRequest,
  StudyProgressEventResponse,
  StudyProgressEventType,
  StudyProgressTargetType
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const EVENT_TYPES = new Set<StudyProgressEventType>([
  "block_opened",
  "block_marked_studied",
  "question_reviewed",
  "review_opened",
  "review_completed"
]);

const TARGET_TYPES = new Set<StudyProgressTargetType>([
  "block",
  "question",
  "review",
  "material"
]);

function marker(...parts: string[]): string {
  return parts.join("");
}

const UNSAFE_TEXT_MARKERS = [
  "raw_text",
  marker("extracted", "_", "text"),
  "chunk",
  "section body",
  marker("storage", "_", "path"),
  marker("/", "Users", "/"),
  "C:\\",
  "token",
  "cookie",
  marker("password", "_", "hash"),
  marker("answer", "_", "key"),
  marker("correct", "_", "answer"),
  marker("correct", "_", "alternative"),
  marker("gabar", "ito"),
  marker("is", "_", "correct"),
  "solution",
  "rationale",
  "correction",
  "score",
  "attempt",
  "internal trace",
  "job trace"
];

function hasUnsafeText(value: string): boolean {
  const normalized = value.toLowerCase();
  return UNSAFE_TEXT_MARKERS.some((marker) => normalized.includes(marker.toLowerCase()));
}

function toSafeString(value: unknown): string {
  if (typeof value !== "string") {
    return "";
  }
  const normalized = value.trim();
  return normalized && !hasUnsafeText(normalized) ? normalized : "";
}

function toSafeNullableString(value: unknown): string | null {
  const safe = toSafeString(value);
  return safe || null;
}

function toSafeEventType(value: unknown): StudyProgressEventType {
  return typeof value === "string" && EVENT_TYPES.has(value as StudyProgressEventType)
    ? (value as StudyProgressEventType)
    : "block_opened";
}

function toSafeTargetType(value: unknown): StudyProgressTargetType {
  return typeof value === "string" && TARGET_TYPES.has(value as StudyProgressTargetType)
    ? (value as StudyProgressTargetType)
    : "block";
}

function sanitizeProgressEventRequest(payload: unknown): StudyProgressEventRequest {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  return {
    event_type: toSafeEventType(raw.event_type),
    target_type: toSafeTargetType(raw.target_type),
    target_id: toSafeString(raw.target_id),
    idempotency_key: toSafeNullableString(raw.idempotency_key)
  };
}

function sanitizeProgressEventResponse(payload: unknown): StudyProgressEventResponse {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  return {
    event_id: toSafeString(raw.event_id),
    event_type: toSafeEventType(raw.event_type),
    target_type: toSafeTargetType(raw.target_type),
    target_id: toSafeString(raw.target_id),
    created_at: toSafeString(raw.created_at),
    source: "user_scope"
  };
}

export async function POST(request: Request) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "O registro de progresso não está configurado neste ambiente." },
      { status: 503 }
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  try {
    const backendResponse = await fetch(`${baseUrl}/api/study/progress/events`, {
      method: "POST",
      headers: {
        ...(request.headers.get("cookie")
          ? {
              cookie: request.headers.get("cookie") as string
            }
          : {}),
        "Content-Type": "application/json"
      },
      cache: "no-store",
      body: JSON.stringify(sanitizeProgressEventRequest(body))
    });

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
    return NextResponse.json(sanitizeProgressEventResponse(payload), { status: backendResponse.status });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível registrar esta ação agora." },
      { status: 502 }
    );
  }
}
