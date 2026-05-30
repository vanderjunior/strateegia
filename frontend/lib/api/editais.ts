import { getJson } from "@/lib/api/client";
import { getApiConfig } from "@/lib/api/config";
import { makeApiFailure } from "@/lib/api/errors";
import type {
  ApiResult,
  BackendBibliographyAlignment,
  BackendEditalExtraction,
  BackendEditalSummary,
  BackendProtectedEditaisList
} from "@/lib/api/types";

export function fetchEditalById(editalId: string): Promise<ApiResult<BackendEditalExtraction>> {
  return getJson<BackendEditalExtraction>(`/api/edital/${editalId}`);
}

export function fetchEditalAlignment(editalId: string): Promise<ApiResult<BackendBibliographyAlignment>> {
  return getJson<BackendBibliographyAlignment>(`/api/edital/${editalId}/alignment`);
}

export async function fetchUserEditaisList(): Promise<ApiResult<BackendProtectedEditaisList>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: a listagem real de editais não foi consultada.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "A listagem real de editais não está configurada neste ambiente."
    );
  }

  try {
    const response = await fetch("/api/editais", {
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
        "A listagem real de editais não está configurada neste ambiente.",
        503
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
      const data = (await response.json()) as BackendProtectedEditaisList;
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
    return makeApiFailure("offline", "network_error", "Não foi possível consultar a listagem real de editais.");
  }
}

export async function fetchEditalSummary(editalId: string): Promise<ApiResult<BackendEditalSummary>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: o resumo real do edital não foi consultado.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "O resumo real do edital não está configurado neste ambiente."
    );
  }

  try {
    const response = await fetch(`/api/editais/${encodeURIComponent(editalId)}/summary`, {
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
        "O resumo real do edital não está configurado neste ambiente.",
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
      const data = (await response.json()) as BackendEditalSummary;
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
    return makeApiFailure("offline", "network_error", "Não foi possível consultar o resumo real do edital.");
  }
}
