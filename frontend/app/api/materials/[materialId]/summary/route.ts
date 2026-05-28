import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type { BackendMaterialSummary } from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function toSafeBoolean(value: unknown): boolean {
  return typeof value === "boolean" ? value : false;
}

function toSafeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toSafeNullableString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function toSafeString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function sanitizePipeline(value: unknown): BackendMaterialSummary["pipeline"] {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    status: toSafeNullableString(raw.status),
    steps_count: toSafeNumber(raw.steps_count),
    has_ocr_warning: toSafeBoolean(raw.has_ocr_warning),
    ready_for_review: toSafeBoolean(raw.ready_for_review)
  };
}

function sanitizeMaterialSummary(payload: unknown): BackendMaterialSummary {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  return {
    document_id: toSafeString(raw.document_id),
    display_filename: toSafeString(raw.display_filename) || "Material da sessão",
    content_type: toSafeString(raw.content_type) || "unknown",
    created_at: toSafeNullableString(raw.created_at),
    updated_at: toSafeNullableString(raw.updated_at),
    processing_status: toSafeString(raw.processing_status) || "unknown",
    extraction_status: toSafeString(raw.extraction_status) || "unknown",
    review_state: toSafeString(raw.review_state) || "unknown",
    chunk_count: toSafeNumber(raw.chunk_count),
    section_count: toSafeNumber(raw.section_count),
    warnings_count: toSafeNumber(raw.warnings_count),
    latest_pipeline_status: toSafeNullableString(raw.latest_pipeline_status),
    pipeline: sanitizePipeline(raw.pipeline),
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
      { detail: "O resumo real do material não está configurado neste ambiente." },
      { status: 503 }
    );
  }

  const { materialId } = await params;

  try {
    const backendResponse = await fetch(
      `${baseUrl}/api/materials/${encodeURIComponent(materialId)}/summary`,
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
    return NextResponse.json(sanitizeMaterialSummary(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar ao backend." },
      { status: 502 }
    );
  }
}
