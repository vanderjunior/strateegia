import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type {
  BackendNextStudySession,
  BackendStudyMaterialSummaryItem,
  StudyMaterialSummaryItemStatus,
  StudyMaterialSummaryStatus,
  StudySessionStatus
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_SESSION_STATUSES = new Set<StudySessionStatus>([
  "ready",
  "needs_review",
  "not_ready"
]);

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
  marker("session", " ", "token"),
  "session=",
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

function toSafeHref(value: unknown, fallback = "/materials"): string {
  const href = toSafeString(value, fallback);
  return href.startsWith("/") && !href.startsWith("//") ? href : fallback;
}

function toSafeSessionStatus(value: unknown): StudySessionStatus {
  return typeof value === "string" && ALLOWED_SESSION_STATUSES.has(value as StudySessionStatus)
    ? (value as StudySessionStatus)
    : "not_ready";
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

function sanitizeActions(value: unknown): { label: string; href: string }[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => {
      const raw = item && typeof item === "object" ? (item as Record<string, unknown>) : {};
      return {
        label: toSafeString(raw.label, "Ver materiais"),
        href: toSafeHref(raw.href)
      };
    })
    .slice(0, 4);
}

function sanitizeNextStudySession(payload: unknown): BackendNextStudySession {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const sessionStatus = toSafeSessionStatus(raw.session_status);
  if (sessionStatus === "not_ready") {
    return {
      session_status: "not_ready",
      message: toSafeString(raw.message, "Envie e prepare um material de estudo para começar."),
      next_actions: sanitizeActions(raw.next_actions),
      source: "user_scope"
    };
  }

  const summaryStatus = toSafeSummaryStatus(raw.summary_status);
  return {
    session_status: sessionStatus,
    session_id: toSafeString(raw.session_id),
    document_id: toSafeString(raw.document_id),
    material_title: toSafeString(raw.material_title, "Material de estudo"),
    material_type: "study_material",
    summary_status: summaryStatus === "ready" ? "ready" : "needs_review",
    estimated_minutes: toSafeNumber(raw.estimated_minutes),
    sections_count: toSafeNumber(raw.sections_count),
    items: Array.isArray(raw.items) ? raw.items.map(sanitizeSummaryItem) : [],
    next_actions: sanitizeActions(raw.next_actions),
    message: toSafeString(raw.message, "Comece por este material preparado."),
    source: "user_scope"
  };
}

export async function GET(request: Request) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "A sessão de estudo não está configurada neste ambiente." },
      { status: 503 }
    );
  }

  try {
    const backendResponse = await fetch(`${baseUrl}/api/study/session/next`, {
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
    return NextResponse.json(sanitizeNextStudySession(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível carregar a sessão agora." },
      { status: 502 }
    );
  }
}
