import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type { BackendEditalAnalysisResponse, EditalAnalysisStatus } from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_ANALYSIS_STATUSES = new Set<EditalAnalysisStatus>([
  "analyzed",
  "needs_review",
  "failed",
  "not_ready",
  "unknown"
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

function sanitizeEditalAnalysis(payload: unknown): BackendEditalAnalysisResponse {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  return {
    edital_id: toSafeString(raw.edital_id),
    document_id: toSafeString(raw.document_id),
    analysis_status: toSafeAnalysisStatus(raw.analysis_status),
    review_state: toSafeString(raw.review_state) || "unknown",
    topics_count: toSafeNumber(raw.topics_count),
    bibliography_count: toSafeNumber(raw.bibliography_count),
    gaps_count: toSafeNumber(raw.gaps_count),
    warnings_count: toSafeNumber(raw.warnings_count),
    source: "user_scope"
  };
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ materialId: string }> }
) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "A análise do edital não está configurada neste ambiente." },
      { status: 503 }
    );
  }

  const { materialId } = await params;

  try {
    const backendResponse = await fetch(
      `${baseUrl}/api/materials/${encodeURIComponent(materialId)}/edital/analyze`,
      {
        method: "POST",
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
    return NextResponse.json(sanitizeEditalAnalysis(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível concluir a análise agora." },
      { status: 502 }
    );
  }
}
