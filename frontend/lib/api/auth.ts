import { getApiConfig } from "@/lib/api/config";
import { makeApiFailure } from "@/lib/api/errors";
import type { ApiResult, BackendCurrentSession } from "@/lib/api/types";

const SESSION_PROXY_PATH = "/api/auth/me";

export async function fetchCurrentSession(): Promise<ApiResult<BackendCurrentSession>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure(
      "mock",
      "mock_mode",
      "Modo de demonstração: a sessão real não foi consultada."
    );
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "Sessão real não configurada neste ambiente."
    );
  }

  try {
    const response = await fetch(SESSION_PROXY_PATH, {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível conectar ao backend.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure("unsupported", "missing_base_url", "Sessão real não configurada neste ambiente.", 503);
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
      const data = (await response.json()) as BackendCurrentSession;
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
    return makeApiFailure("offline", "network_error", "Não foi possível confirmar a sessão agora.");
  }
}
