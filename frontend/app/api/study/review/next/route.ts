import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type {
  BackendNextReviewBlock,
  BackendStudyBlockAction,
  ReviewBlockBasis,
  ReviewBlockSectionStatus,
  ReviewBlockStatus
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_REVIEW_STATUSES = new Set<ReviewBlockStatus>([
  "ready",
  "partial",
  "not_ready",
  "needs_review"
]);

const ALLOWED_BASES = new Set<ReviewBlockBasis>([
  "prepared_materials",
  "study_blocks"
]);

const ALLOWED_SECTION_STATUSES = new Set<ReviewBlockSectionStatus>([
  "ready",
  "needs_review",
  "not_ready"
]);

function marker(...parts: string[]): string {
  return parts.join("");
}

const UNSAFE_TEXT_MARKERS = [
  "raw_text",
  marker("extracted", "_", "text"),
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
  marker("answer", "_", "key"),
  marker("correct", "_", "answer"),
  marker("correct", "_", "alternative"),
  marker("gabar", "ito"),
  marker("is", "_", "correct"),
  "solution",
  "rationale",
  "correction",
  "score",
  "progress",
  "attempt",
  "worker",
  "job trace",
  "internal trace"
];

function hasUnsafeText(value: string): boolean {
  const normalized = value.toLowerCase();
  return UNSAFE_TEXT_MARKERS.some((marker) => normalized.includes(marker.toLowerCase()));
}

function toSafeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
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

function toSafeHref(value: unknown, fallback = "/study"): string {
  const href = toSafeString(value, fallback);
  return href.startsWith("/") && !href.startsWith("//") ? href : fallback;
}

function toSafeReviewStatus(value: unknown): ReviewBlockStatus {
  return typeof value === "string" && ALLOWED_REVIEW_STATUSES.has(value as ReviewBlockStatus)
    ? (value as ReviewBlockStatus)
    : "not_ready";
}

function toSafeBasis(value: unknown): ReviewBlockBasis {
  return typeof value === "string" && ALLOWED_BASES.has(value as ReviewBlockBasis)
    ? (value as ReviewBlockBasis)
    : "prepared_materials";
}

function toSafeSectionStatus(value: unknown): ReviewBlockSectionStatus {
  return typeof value === "string" && ALLOWED_SECTION_STATUSES.has(value as ReviewBlockSectionStatus)
    ? (value as ReviewBlockSectionStatus)
    : "not_ready";
}

function sanitizeSummaryItem(value: unknown): BackendNextReviewBlock["summary"]["items"][number] {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    title: toSafeString(raw.title, "Ponto para revisar"),
    message: toSafeString(raw.message, "Revise os pontos principais dos materiais preparados."),
    topic_label: toSafeNullableString(raw.topic_label),
    subtopic_label: toSafeNullableString(raw.subtopic_label)
  };
}

function sanitizeSummary(value: unknown): BackendNextReviewBlock["summary"] {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    status: toSafeSectionStatus(raw.status),
    items: Array.isArray(raw.items) ? raw.items.map(sanitizeSummaryItem).slice(0, 8) : []
  };
}

function sanitizeQuestions(value: unknown): BackendNextReviewBlock["questions"] {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    status: toSafeSectionStatus(raw.status),
    items_count: toSafeNumber(raw.items_count)
  };
}

function sanitizeReinforcementItem(value: unknown): BackendNextReviewBlock["reinforcement"]["items"][number] {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    topic_label: toSafeNullableString(raw.topic_label),
    subtopic_label: toSafeNullableString(raw.subtopic_label),
    message: toSafeString(
      raw.message,
      "Ainda não há histórico suficiente para destacar pontos fracos reais."
    )
  };
}

function sanitizeReinforcement(value: unknown): BackendNextReviewBlock["reinforcement"] {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    status: toSafeSectionStatus(raw.status),
    weak_topics_count: toSafeNumber(raw.weak_topics_count),
    items: Array.isArray(raw.items) ? raw.items.map(sanitizeReinforcementItem).slice(0, 8) : []
  };
}

function sanitizeAction(value: unknown): BackendStudyBlockAction {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    label: toSafeString(raw.label, "Abrir revisão"),
    href: toSafeHref(raw.href)
  };
}

function sanitizeActions(value: unknown): BackendStudyBlockAction[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map(sanitizeAction).slice(0, 4);
}

function sanitizeNextReviewBlock(payload: unknown): BackendNextReviewBlock {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const reviewStatus = toSafeReviewStatus(raw.review_status);
  const data: BackendNextReviewBlock = {
    review_status: reviewStatus,
    review_id: reviewStatus === "not_ready" ? null : toSafeNullableString(raw.review_id),
    basis: toSafeBasis(raw.basis),
    materials_count: toSafeNumber(raw.materials_count),
    blocks_count: toSafeNumber(raw.blocks_count),
    estimated_minutes: toSafeNumber(raw.estimated_minutes),
    title: toSafeString(raw.title, "Revisão acumulada"),
    summary: sanitizeSummary(raw.summary),
    questions: sanitizeQuestions(raw.questions),
    reinforcement: sanitizeReinforcement(raw.reinforcement),
    actions: sanitizeActions(raw.actions),
    source: "user_scope"
  };

  if (reviewStatus === "not_ready" || typeof raw.message === "string") {
    data.message = toSafeString(
      raw.message,
      "Prepare pelo menos 3 materiais de estudo para montar uma revisão acumulada."
    );
  }

  return data;
}

export async function GET(request: Request) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "A revisão acumulada não está configurada neste ambiente." },
      { status: 503 }
    );
  }

  try {
    const backendResponse = await fetch(`${baseUrl}/api/study/review/next`, {
      method: "GET",
      headers: request.headers.get("cookie")
        ? {
            cookie: request.headers.get("cookie") as string
          }
        : undefined,
      cache: "no-store"
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
    return NextResponse.json(sanitizeNextReviewBlock(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível carregar a revisão agora." },
      { status: 502 }
    );
  }
}
