import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type {
  BackendStudyBlockAction,
  BackendStudyBlockDetail,
  BackendStudyBlockDetailStatus,
  StudyBlockItemStatus,
  StudyMaterialSummaryStatus
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_DETAIL_STATUSES = new Set<BackendStudyBlockDetailStatus>([
  "ready",
  "needs_review",
  "not_ready"
]);

const ALLOWED_SUMMARY_STATUSES = new Set<StudyMaterialSummaryStatus>([
  "ready",
  "needs_review",
  "not_ready"
]);

const ALLOWED_SECTION_STATUSES = new Set<StudyBlockItemStatus>([
  "ready",
  "needs_review"
]);

function marker(...parts: string[]): string {
  return parts.join("");
}

const UNSAFE_TEXT_MARKERS = [
  "raw_text",
  marker("extracted", "_", "text"),
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
  marker("answer", "_", "key"),
  marker("gabar", "ito"),
  marker("correct", "ness"),
  marker("is", "_", "correct"),
  "progress",
  "correction",
  "worker",
  "job trace",
  "internal trace",
  "evidence"
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

function toSafeDetailStatus(value: unknown): BackendStudyBlockDetailStatus {
  return typeof value === "string" && ALLOWED_DETAIL_STATUSES.has(value as BackendStudyBlockDetailStatus)
    ? (value as BackendStudyBlockDetailStatus)
    : "not_ready";
}

function toSafeSummaryStatus(value: unknown): Exclude<StudyMaterialSummaryStatus, "failed"> {
  return typeof value === "string" && ALLOWED_SUMMARY_STATUSES.has(value as StudyMaterialSummaryStatus)
    ? (value as Exclude<StudyMaterialSummaryStatus, "failed">)
    : "not_ready";
}

function toSafeSectionStatus(value: unknown): "ready" | "needs_review" {
  return typeof value === "string" && ALLOWED_SECTION_STATUSES.has(value as StudyBlockItemStatus)
    ? (value as "ready" | "needs_review")
    : "needs_review";
}

function sanitizeKeyPoints(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => toSafeString(item))
    .filter(Boolean)
    .slice(0, 8);
}

function sanitizeSection(value: unknown): BackendStudyBlockDetail["sections"][number] {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    section_id: toSafeString(raw.section_id),
    title: toSafeString(raw.title, "Seção do material"),
    summary: toSafeString(raw.summary, "Resumo em preparação para esta seção."),
    key_points: sanitizeKeyPoints(raw.key_points),
    estimated_minutes: toSafeNumber(raw.estimated_minutes),
    status: toSafeSectionStatus(raw.status)
  };
}

function sanitizeActions(value: unknown): BackendStudyBlockAction[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => {
      const raw = item && typeof item === "object" ? (item as Record<string, unknown>) : {};
      return {
        label: toSafeString(raw.label, "Voltar ao caminho de estudo"),
        href: toSafeHref(raw.href)
      };
    })
    .slice(0, 4);
}

function sanitizeStudyBlockDetail(payload: unknown): BackendStudyBlockDetail {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  return {
    block_id: toSafeString(raw.block_id),
    detail_status: toSafeDetailStatus(raw.detail_status),
    title: toSafeString(raw.title, "Bloco de estudo"),
    topic_id: toSafeNullableString(raw.topic_id),
    topic_label: toSafeNullableString(raw.topic_label),
    subtopic_id: toSafeNullableString(raw.subtopic_id),
    subtopic_label: toSafeNullableString(raw.subtopic_label),
    material_id: toSafeString(raw.material_id),
    material_title: toSafeString(raw.material_title, "Material de estudo"),
    summary_status: toSafeSummaryStatus(raw.summary_status),
    estimated_minutes: toSafeNumber(raw.estimated_minutes),
    sections: Array.isArray(raw.sections) ? raw.sections.map(sanitizeSection) : [],
    actions: sanitizeActions(raw.actions),
    source: "user_scope"
  };
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ blockId: string }> }
) {
  const baseUrl = getServerBackendBaseUrl();
  const { blockId } = await params;

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "Este bloco de estudo não está configurado neste ambiente." },
      { status: 503 }
    );
  }

  try {
    const backendResponse = await fetch(`${baseUrl}/api/study/blocks/${encodeURIComponent(blockId)}`, {
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
    return NextResponse.json(sanitizeStudyBlockDetail(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível carregar este bloco agora." },
      { status: 502 }
    );
  }
}
