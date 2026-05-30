import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type { BackendProtectedMaterialsList, MaterialType } from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function toSafeNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function toSafeString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

const ALLOWED_MATERIAL_TYPES = new Set<MaterialType>([
  "edital",
  "study_material",
  "previous_exam",
  "bibliography",
  "note",
  "other",
  "unknown"
]);

function toSafeMaterialType(value: unknown): MaterialType {
  return typeof value === "string" && ALLOWED_MATERIAL_TYPES.has(value as MaterialType)
    ? (value as MaterialType)
    : "unknown";
}

function toSafeDateString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function sanitizeMaterialsList(payload: unknown): BackendProtectedMaterialsList {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const rawItems = Array.isArray(raw.items) ? raw.items : [];
  const items = rawItems.map((item) => {
    const rawItem = item && typeof item === "object" ? (item as Record<string, unknown>) : {};
    const processingStatus = toSafeString(rawItem.processing_status);
    const latestPipelineStatus = toSafeString(rawItem.latest_pipeline_status);
    const extractionStatus = toSafeString(rawItem.extraction_status);

    return {
      document_id: toSafeString(rawItem.document_id),
      display_filename: toSafeString(rawItem.display_filename),
      content_type: toSafeString(rawItem.content_type),
      material_type: toSafeMaterialType(rawItem.material_type),
      status: processingStatus,
      uploaded_at: toSafeDateString(rawItem.created_at),
      extraction_status: extractionStatus,
      current_stage: latestPipelineStatus || processingStatus,
      metadata_status: rawItem.review_state === "ready_for_review" ? "ready" : "not_ready",
      chunk_count: toSafeNumber(rawItem.chunk_count),
      section_count: toSafeNumber(rawItem.section_count)
    };
  });

  const processedCount = items.filter((item) =>
    ["ready_for_review", "text_extracted"].includes(item.status)
  ).length;
  const pendingCount = items.filter((item) =>
    ["uploaded", "extraction_pending", "unknown"].includes(item.status)
  ).length;
  const ocrRequiredCount = items.filter((item) =>
    item.status.includes("ocr") || item.extraction_status.includes("ocr")
  ).length;

  return {
    total_materials: toSafeNumber(raw.count) ?? items.length,
    processed_count: processedCount,
    pending_count: pendingCount,
    ocr_required_count: ocrRequiredCount,
    items
  };
}

export async function GET(request: Request) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "A listagem real de materiais não está configurada neste ambiente." },
      { status: 503 }
    );
  }

  try {
    const backendResponse = await fetch(`${baseUrl}/api/materials`, {
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
    return NextResponse.json(sanitizeMaterialsList(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível carregar os dados agora." },
      { status: 502 }
    );
  }
}
