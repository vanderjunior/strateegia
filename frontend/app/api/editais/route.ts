import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type { BackendProtectedEditaisList } from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function toSafeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toSafeString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function statusLabelForReviewState(value: string): string {
  if (value === "ready_for_review") {
    return "Análise candidata";
  }
  return "Análise candidata";
}

function reviewLabelForState(value: string): string {
  if (value === "ready_for_review") {
    return "Pronto para revisão";
  }
  if (value === "pending") {
    return "Alinhamento preliminar";
  }
  return "Precisa de conferência";
}

function coverageLabelForState(value: string): string {
  if (value === "good") {
    return "Cobertura boa";
  }
  if (value === "gap_found") {
    return "Gap encontrado";
  }
  if (value === "needs_material") {
    return "Precisa de material";
  }
  if (value === "partial") {
    return "Cobertura parcial";
  }
  return "Alinhamento preliminar";
}

function sanitizeEditaisList(payload: unknown): BackendProtectedEditaisList {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const rawItems = Array.isArray(raw.items) ? raw.items : [];
  const items = rawItems.map((item) => {
    const rawItem = item && typeof item === "object" ? (item as Record<string, unknown>) : {};
    const reviewState = toSafeString(rawItem.review_state);
    const coverageStatus = toSafeString(rawItem.coverage_status);

    return {
      edital_id: toSafeString(rawItem.edital_id),
      title: toSafeString(rawItem.title) || "Edital analisado da sessão",
      status: statusLabelForReviewState(reviewState),
      review_state: reviewLabelForState(reviewState),
      topics_count: toSafeNumber(rawItem.topics_count),
      bibliography_count: toSafeNumber(rawItem.bibliography_count),
      gaps_count: toSafeNumber(rawItem.gaps_count),
      coverage_status: coverageLabelForState(coverageStatus),
      latest_document_id: toSafeString(rawItem.document_id) || null
    };
  });

  return {
    total_editais: toSafeNumber(raw.count) || items.length,
    total_topics: items.reduce((total, item) => total + item.topics_count, 0),
    total_bibliography_items: items.reduce((total, item) => total + item.bibliography_count, 0),
    total_gaps: items.reduce((total, item) => total + item.gaps_count, 0),
    items
  };
}

export async function GET(request: Request) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "A listagem real de editais não está configurada neste ambiente." },
      { status: 503 }
    );
  }

  try {
    const backendResponse = await fetch(`${baseUrl}/api/editais`, {
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
    return NextResponse.json(sanitizeEditaisList(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar ao backend." },
      { status: 502 }
    );
  }
}
