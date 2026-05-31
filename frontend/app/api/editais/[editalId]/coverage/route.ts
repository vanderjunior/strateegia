import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type { BackendEditalCoverage, EditalAnalysisStatus, EditalCoverageItemStatus, EditalCoverageStatus } from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_ANALYSIS_STATUSES = new Set<EditalAnalysisStatus>([
  "uploaded_not_analyzed",
  "analyzed",
  "needs_review",
  "failed",
  "not_ready",
  "unknown"
]);

const ALLOWED_COVERAGE_STATUSES = new Set<EditalCoverageStatus>([
  "not_ready",
  "partial",
  "ready_for_review",
  "needs_review",
  "unknown"
]);

const ALLOWED_ITEM_STATUSES = new Set<EditalCoverageItemStatus>([
  "covered",
  "partial",
  "uncovered",
  "needs_review"
]);

function toSafeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toSafeString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function toSafeAnalysisStatus(value: unknown): EditalAnalysisStatus {
  return typeof value === "string" && ALLOWED_ANALYSIS_STATUSES.has(value as EditalAnalysisStatus)
    ? (value as EditalAnalysisStatus)
    : "unknown";
}

function toSafeCoverageStatus(value: unknown): EditalCoverageStatus {
  return typeof value === "string" && ALLOWED_COVERAGE_STATUSES.has(value as EditalCoverageStatus)
    ? (value as EditalCoverageStatus)
    : "unknown";
}

function toSafeItemStatus(value: unknown): EditalCoverageItemStatus {
  return typeof value === "string" && ALLOWED_ITEM_STATUSES.has(value as EditalCoverageItemStatus)
    ? (value as EditalCoverageItemStatus)
    : "needs_review";
}

function sanitizeEditalCoverage(payload: unknown): BackendEditalCoverage {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const rawItems = Array.isArray(raw.items) ? raw.items : [];
  const items = rawItems.map((item) => {
    const rawItem = item && typeof item === "object" ? (item as Record<string, unknown>) : {};
    return {
      topic_id: toSafeString(rawItem.topic_id),
      label: toSafeString(rawItem.label),
      subtopics_count: toSafeNumber(rawItem.subtopics_count),
      covered_count: toSafeNumber(rawItem.covered_count),
      partial_count: toSafeNumber(rawItem.partial_count),
      uncovered_count: toSafeNumber(rawItem.uncovered_count),
      status: toSafeItemStatus(rawItem.status)
    };
  });

  return {
    edital_id: toSafeString(raw.edital_id),
    analysis_status: toSafeAnalysisStatus(raw.analysis_status),
    coverage_status: toSafeCoverageStatus(raw.coverage_status),
    topics_count: toSafeNumber(raw.topics_count),
    subtopics_count: toSafeNumber(raw.subtopics_count),
    covered_subtopics_count: toSafeNumber(raw.covered_subtopics_count),
    partial_subtopics_count: toSafeNumber(raw.partial_subtopics_count),
    uncovered_subtopics_count: toSafeNumber(raw.uncovered_subtopics_count),
    out_of_scope_materials_count: toSafeNumber(raw.out_of_scope_materials_count),
    materials_considered_count: toSafeNumber(raw.materials_considered_count),
    items,
    source: "user_scope"
  };
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ editalId: string }> }
) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "A cobertura do edital não está configurada neste ambiente." },
      { status: 503 }
    );
  }

  const { editalId: routeEditalId } = await params;
  const editalId = safeDecodeRouteParam(routeEditalId);

  try {
    const backendResponse = await fetch(
      `${baseUrl}/api/editais/${encodeURIComponent(editalId)}/coverage`,
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
    return NextResponse.json(sanitizeEditalCoverage(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível consultar a cobertura agora." },
      { status: 502 }
    );
  }
}

function safeDecodeRouteParam(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
