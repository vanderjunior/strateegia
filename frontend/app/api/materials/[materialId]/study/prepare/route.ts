import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type {
  BackendStudyMaterialPreparationResponse,
  StudyMaterialPreparationStatus
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ALLOWED_PREPARATION_STATUSES = new Set<StudyMaterialPreparationStatus>([
  "ready_for_study",
  "needs_review",
  "not_ready",
  "failed"
]);

function toSafeBoolean(value: unknown): boolean {
  return typeof value === "boolean" ? value : false;
}

function toSafeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toSafeString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function toSafePreparationStatus(value: unknown): StudyMaterialPreparationStatus {
  return typeof value === "string" && ALLOWED_PREPARATION_STATUSES.has(value as StudyMaterialPreparationStatus)
    ? (value as StudyMaterialPreparationStatus)
    : "not_ready";
}

function sanitizeStudyMaterialPreparation(payload: unknown): BackendStudyMaterialPreparationResponse {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  return {
    document_id: toSafeString(raw.document_id),
    preparation_status: toSafePreparationStatus(raw.preparation_status),
    material_type: "study_material",
    section_count: toSafeNumber(raw.section_count),
    chunk_count: toSafeNumber(raw.chunk_count),
    warnings_count: toSafeNumber(raw.warnings_count),
    ready_for_study: toSafeBoolean(raw.ready_for_study),
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
      { detail: "A preparação do material não está configurada neste ambiente." },
      { status: 503 }
    );
  }

  const { materialId } = await params;

  try {
    const backendResponse = await fetch(
      `${baseUrl}/api/materials/${encodeURIComponent(materialId)}/study/prepare`,
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
    return NextResponse.json(sanitizeStudyMaterialPreparation(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível preparar o material agora." },
      { status: 502 }
    );
  }
}
