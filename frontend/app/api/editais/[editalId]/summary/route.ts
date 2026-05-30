import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type { BackendEditalSummary } from "@/lib/api/types";

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

function sanitizeSummary(value: unknown): BackendEditalSummary["summary"] {
  const raw = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  return {
    has_topics: toSafeBoolean(raw.has_topics),
    has_bibliography: toSafeBoolean(raw.has_bibliography),
    has_gaps: toSafeBoolean(raw.has_gaps),
    needs_review: toSafeBoolean(raw.needs_review)
  };
}

function sanitizeEditalSummary(payload: unknown): BackendEditalSummary {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  return {
    edital_id: toSafeString(raw.edital_id),
    document_id: toSafeNullableString(raw.document_id),
    title: toSafeString(raw.title) || "Edital analisado da sessão",
    created_at: toSafeNullableString(raw.created_at),
    updated_at: toSafeNullableString(raw.updated_at),
    topics_count: toSafeNumber(raw.topics_count),
    bibliography_count: toSafeNumber(raw.bibliography_count),
    gaps_count: toSafeNumber(raw.gaps_count),
    review_state: toSafeString(raw.review_state) || "unknown",
    coverage_status: toSafeString(raw.coverage_status) || "unknown",
    alignment_status: toSafeString(raw.alignment_status) || "unknown",
    warnings_count: toSafeNumber(raw.warnings_count),
    summary: sanitizeSummary(raw.summary),
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
      { detail: "O resumo real do edital não está configurado neste ambiente." },
      { status: 503 }
    );
  }

  const { editalId } = await params;

  try {
    const backendResponse = await fetch(
      `${baseUrl}/api/editais/${encodeURIComponent(editalId)}/summary`,
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
    return NextResponse.json(sanitizeEditalSummary(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível carregar os dados agora." },
      { status: 502 }
    );
  }
}
