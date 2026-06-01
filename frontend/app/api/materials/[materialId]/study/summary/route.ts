import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type {
  BackendStudyMaterialSummary,
  BackendStudyMaterialSummaryItem,
  StudyMaterialSummaryItemStatus,
  StudyMaterialSummaryStatus
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_SUMMARY_STATUSES = new Set<StudyMaterialSummaryStatus>([
  "ready",
  "needs_review",
  "not_ready",
  "failed"
]);

const ALLOWED_ITEM_STATUSES = new Set<StudyMaterialSummaryItemStatus>([
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
  "session",
  marker("password", "_", "hash"),
  marker("answer", "_", "key"),
  marker("gabar", "ito"),
  marker("correct", "ness"),
  marker("is", "_", "correct"),
  "worker",
  "job trace"
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

function toSafeSummaryStatus(value: unknown): StudyMaterialSummaryStatus {
  return typeof value === "string" && ALLOWED_SUMMARY_STATUSES.has(value as StudyMaterialSummaryStatus)
    ? (value as StudyMaterialSummaryStatus)
    : "not_ready";
}

function toSafeItemStatus(value: unknown): StudyMaterialSummaryItemStatus {
  return typeof value === "string" && ALLOWED_ITEM_STATUSES.has(value as StudyMaterialSummaryItemStatus)
    ? (value as StudyMaterialSummaryItemStatus)
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

function sanitizeSummaryItem(value: unknown): BackendStudyMaterialSummaryItem {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    section_id: toSafeString(raw.section_id),
    title: toSafeString(raw.title, "Seção do material"),
    summary: toSafeString(raw.summary, "Resumo em preparação para esta seção."),
    key_points: sanitizeKeyPoints(raw.key_points),
    estimated_minutes: toSafeNumber(raw.estimated_minutes),
    status: toSafeItemStatus(raw.status)
  };
}

function sanitizeStudyMaterialSummary(payload: unknown): BackendStudyMaterialSummary {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const items = Array.isArray(raw.items) ? raw.items.map(sanitizeSummaryItem) : [];
  return {
    document_id: toSafeString(raw.document_id),
    summary_status: toSafeSummaryStatus(raw.summary_status),
    material_type: "study_material",
    title: toSafeString(raw.title, "Material de estudo"),
    sections_count: toSafeNumber(raw.sections_count),
    items,
    warnings_count: toSafeNumber(raw.warnings_count),
    source: "user_scope"
  };
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ materialId: string }> }
) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "O resumo do material não está configurado neste ambiente." },
      { status: 503 }
    );
  }

  const { materialId } = await params;

  try {
    const backendResponse = await fetch(
      `${baseUrl}/api/materials/${encodeURIComponent(materialId)}/study/summary`,
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
    return NextResponse.json(sanitizeStudyMaterialSummary(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível consultar o resumo agora." },
      { status: 502 }
    );
  }
}
