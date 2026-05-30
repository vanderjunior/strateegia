import { getJson } from "@/lib/api/client";
import { getApiConfig } from "@/lib/api/config";
import { makeApiFailure } from "@/lib/api/errors";
import type {
  ApiResult,
  BackendDocumentChunk,
  BackendDocumentPipelineState,
  BackendDocumentSection,
  BackendPipelineSummary
} from "@/lib/api/types";

export function fetchMaterialPipelineState(
  documentId: string
): Promise<ApiResult<BackendDocumentPipelineState>> {
  return getJson<BackendDocumentPipelineState>(`/api/materials/${documentId}/pipeline`);
}

export function fetchMaterialSections(
  documentId: string
): Promise<ApiResult<BackendDocumentSection[]>> {
  return getJson<BackendDocumentSection[]>(`/api/materials/${documentId}/sections`);
}

export function fetchMaterialChunks(documentId: string): Promise<ApiResult<BackendDocumentChunk[]>> {
  return getJson<BackendDocumentChunk[]>(`/api/materials/${documentId}/chunks`);
}

export async function fetchPipelineSummary(documentId: string): Promise<ApiResult<BackendPipelineSummary>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: o resumo real do pipeline não foi consultado.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "O resumo real do pipeline não está configurado neste ambiente."
    );
  }

  try {
    const response = await fetch(`/api/materials/${encodeURIComponent(documentId)}/pipeline/summary`, {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível carregar os dados agora.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "O resumo real do pipeline não está configurado neste ambiente.",
        503
      );
    }
    if (response.status === 404) {
      return makeApiFailure(
        "backend",
        "not_found",
        "Este conteúdo não está disponível nesta sessão.",
        404
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "unauthorized", "Sessão necessária.", response.status);
    }
    if (!response.ok) {
      return makeApiFailure(
        "backend",
        "http_error",
        `Backend returned HTTP ${response.status}.`,
        response.status
      );
    }

    try {
      const data = (await response.json()) as BackendPipelineSummary;
      return {
        ok: true,
        data,
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_json", "Backend returned invalid JSON.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "network_error", "Não foi possível consultar o resumo real do pipeline.");
  }
}
