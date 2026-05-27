import { NextResponse } from "next/server";

import type {
  BackendDashboardOverview,
  BackendDashboardPipelineStateItem,
  BackendDashboardRecentMaterialItem,
  BackendProtectedMaterialsList
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function getBackendBaseUrl(): string | null {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return value ? value.replace(/\/+$/, "") : null;
}

function toSafeNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function sanitizeMaterialsList(overview: BackendDashboardOverview): BackendProtectedMaterialsList {
  const statesByDocumentId = new Map<string, BackendDashboardPipelineStateItem>(
    overview.document_pipeline.latest_pipeline_states.map((item) => [item.document_id, item])
  );

  return {
    total_materials: overview.materials.total_materials,
    processed_count: overview.materials.processed_count,
    pending_count: overview.materials.pending_count,
    ocr_required_count: overview.materials.ocr_required_count,
    items: overview.materials.recent_materials.map((item: BackendDashboardRecentMaterialItem) => {
      const state = statesByDocumentId.get(item.document_id);
      const metadata = state?.metadata ?? {};

      return {
        document_id: item.document_id,
        display_filename: item.display_filename,
        content_type: item.content_type ?? "",
        status: item.status ?? "",
        uploaded_at: item.uploaded_at ?? null,
        extraction_status: state?.extraction_status ?? "",
        current_stage: state?.current_stage ?? "",
        metadata_status: state?.metadata_status ?? "",
        chunk_count: toSafeNumber(metadata.chunk_count),
        section_count: toSafeNumber(metadata.section_count)
      };
    })
  };
}

export async function GET(request: Request) {
  const baseUrl = getBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "A listagem real de materiais não está configurada neste ambiente." },
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
    return NextResponse.json(sanitizeMaterialsList(overview), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar ao backend." },
      { status: 502 }
    );
  }
}
