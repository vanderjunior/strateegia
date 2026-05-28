import { NextResponse } from "next/server";

import type { BackendPipelineSummary } from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function getBackendBaseUrl(): string | null {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return value ? value.replace(/\/+$/, "") : null;
}

function toSafeBoolean(value: unknown): boolean {
  return typeof value === "boolean" ? value : false;
}

function toSafeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toSafeString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function sanitizeSteps(value: unknown): BackendPipelineSummary["steps"] {
  const rawSteps = Array.isArray(value) ? value : [];
  return rawSteps.map((step) => {
    const raw = step && typeof step === "object" ? (step as Record<string, unknown>) : {};
    return {
      key: toSafeString(raw.key) || "unknown",
      label: toSafeString(raw.label) || "Etapa em validação",
      state: toSafeString(raw.state) || "unknown",
      warnings_count: toSafeNumber(raw.warnings_count)
    };
  });
}

function sanitizePipelineSummary(payload: unknown): BackendPipelineSummary {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const steps = sanitizeSteps(raw.steps);
  return {
    document_id: toSafeString(raw.document_id),
    status: toSafeString(raw.status) || "unknown",
    steps,
    steps_count: toSafeNumber(raw.steps_count) || steps.length,
    has_ocr_warning: toSafeBoolean(raw.has_ocr_warning),
    ready_for_review: toSafeBoolean(raw.ready_for_review),
    section_count: toSafeNumber(raw.section_count),
    chunk_count: toSafeNumber(raw.chunk_count),
    warnings_count: toSafeNumber(raw.warnings_count),
    source: "user_scope"
  };
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ materialId: string }> }
) {
  const baseUrl = getBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "O resumo real do pipeline não está configurado neste ambiente." },
      { status: 503 }
    );
  }

  const { materialId } = await params;

  try {
    const backendResponse = await fetch(
      `${baseUrl}/api/materials/${encodeURIComponent(materialId)}/pipeline/summary`,
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
    return NextResponse.json(sanitizePipelineSummary(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar ao backend." },
      { status: 502 }
    );
  }
}
