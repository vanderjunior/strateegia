import { NextResponse } from "next/server";

import type {
  BackendDashboardOverview,
  BackendProtectedEditaisList,
  BackendProtectedEditaisListItem
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function getBackendBaseUrl(): string | null {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return value ? value.replace(/\/+$/, "") : null;
}

function coverageStatusForOverview(overview: BackendDashboardOverview): string {
  if (!overview.alignment.alignment_available) {
    return "Alinhamento preliminar";
  }
  if (overview.alignment.gaps_detected > 0) {
    return "Cobertura parcial";
  }
  return "Cobertura boa";
}

function buildItemFromOverview(overview: BackendDashboardOverview): BackendProtectedEditaisListItem | null {
  if (!overview.edital.edital_available || !overview.edital.latest_edital_id) {
    return null;
  }

  const needsReview = Boolean(overview.edital.needs_review) || Boolean(overview.alignment.needs_review);

  return {
    edital_id: overview.edital.latest_edital_id,
    title: "Edital analisado da sessão",
    status: "Análise candidata",
    review_state: needsReview ? "Precisa de conferência" : "Pronto para revisão",
    topics_count: overview.edital.topics_detected ?? overview.alignment.topics_total ?? 0,
    bibliography_count:
      overview.edital.bibliography_items_detected ?? overview.alignment.bibliography_items_total ?? 0,
    gaps_count: overview.alignment.gaps_detected,
    coverage_status: coverageStatusForOverview(overview),
    latest_document_id: overview.edital.latest_document_id ?? null
  };
}

function sanitizeEditaisList(overview: BackendDashboardOverview): BackendProtectedEditaisList {
  const item = buildItemFromOverview(overview);
  const items = item ? [item] : [];

  return {
    total_editais: items.length,
    total_topics: item?.topics_count ?? 0,
    total_bibliography_items: item?.bibliography_count ?? 0,
    total_gaps: item?.gaps_count ?? 0,
    items
  };
}

export async function GET(request: Request) {
  const baseUrl = getBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "A listagem real de editais não está configurada neste ambiente." },
      { status: 503 }
    );
  }

  try {
    const backendResponse = await fetch(`${baseUrl}/api/dashboard/overview`, {
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

    const overview = (await backendResponse.json()) as BackendDashboardOverview;
    return NextResponse.json(sanitizeEditaisList(overview), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar ao backend." },
      { status: 502 }
    );
  }
}
