import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type {
  BackendStudyBlockAction,
  BackendStudyBlockItem,
  BackendStudyBlocks,
  StudyBlockItemStatus,
  StudyBlocksScopeStatus,
  StudyBlocksStatus,
  StudyMaterialSummaryStatus
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_BLOCK_STATUSES = new Set<StudyBlocksStatus>([
  "ready",
  "partial",
  "not_ready",
  "needs_review"
]);

const ALLOWED_SCOPE_STATUSES = new Set<StudyBlocksScopeStatus>([
  "connected_to_edital",
  "material_only",
  "not_ready"
]);

const ALLOWED_SUMMARY_STATUSES = new Set<StudyMaterialSummaryStatus>([
  "ready",
  "needs_review",
  "not_ready",
  "failed"
]);

const ALLOWED_ITEM_STATUSES = new Set<StudyBlockItemStatus>([
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

function toSafeBlocksStatus(value: unknown): StudyBlocksStatus {
  return typeof value === "string" && ALLOWED_BLOCK_STATUSES.has(value as StudyBlocksStatus)
    ? (value as StudyBlocksStatus)
    : "not_ready";
}

function toSafeScopeStatus(value: unknown): StudyBlocksScopeStatus {
  return typeof value === "string" && ALLOWED_SCOPE_STATUSES.has(value as StudyBlocksScopeStatus)
    ? (value as StudyBlocksScopeStatus)
    : "not_ready";
}

function toSafeSummaryStatus(value: unknown): StudyMaterialSummaryStatus {
  return typeof value === "string" && ALLOWED_SUMMARY_STATUSES.has(value as StudyMaterialSummaryStatus)
    ? (value as StudyMaterialSummaryStatus)
    : "not_ready";
}

function toSafeItemStatus(value: unknown): StudyBlockItemStatus {
  return typeof value === "string" && ALLOWED_ITEM_STATUSES.has(value as StudyBlockItemStatus)
    ? (value as StudyBlockItemStatus)
    : "needs_review";
}

function sanitizeAction(value: unknown): BackendStudyBlockAction {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    label: toSafeString(raw.label, "Estudar bloco"),
    href: toSafeHref(raw.href)
  };
}

function sanitizeActions(value: unknown): BackendStudyBlockAction[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map(sanitizeAction).slice(0, 4);
}

function sanitizeStudyBlockItem(value: unknown): BackendStudyBlockItem {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    block_id: toSafeString(raw.block_id),
    title: toSafeString(raw.title, "Bloco de estudo"),
    topic_id: toSafeNullableString(raw.topic_id),
    topic_label: toSafeNullableString(raw.topic_label),
    subtopic_id: toSafeNullableString(raw.subtopic_id),
    subtopic_label: toSafeNullableString(raw.subtopic_label),
    material_id: toSafeString(raw.material_id),
    material_title: toSafeString(raw.material_title, "Material de estudo"),
    sections_count: toSafeNumber(raw.sections_count),
    summary_status: toSafeSummaryStatus(raw.summary_status),
    estimated_minutes: toSafeNumber(raw.estimated_minutes),
    status: toSafeItemStatus(raw.status),
    actions: sanitizeActions(raw.actions)
  };
}

function sanitizeStudyBlocks(payload: unknown): BackendStudyBlocks {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const blocksStatus = toSafeBlocksStatus(raw.blocks_status);
  const data: BackendStudyBlocks = {
    blocks_status: blocksStatus,
    scope_status: blocksStatus === "not_ready" ? "not_ready" : toSafeScopeStatus(raw.scope_status),
    blocks_count: toSafeNumber(raw.blocks_count),
    estimated_minutes: toSafeNumber(raw.estimated_minutes),
    items: Array.isArray(raw.items) ? raw.items.map(sanitizeStudyBlockItem) : [],
    source: "user_scope"
  };

  if (blocksStatus === "not_ready" || typeof raw.message === "string") {
    data.message = toSafeString(raw.message, "Envie e prepare um material de estudo para montar seus blocos.");
  }

  return data;
}

export async function GET(request: Request) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "Os blocos de estudo não estão configurados neste ambiente." },
      { status: 503 }
    );
  }

  try {
    const backendResponse = await fetch(`${baseUrl}/api/study/blocks`, {
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
    return NextResponse.json(sanitizeStudyBlocks(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível carregar seus blocos agora." },
      { status: 502 }
    );
  }
}
