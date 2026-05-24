import { getApiConfig } from "@/lib/api/config";
import { makeApiFailure } from "@/lib/api/errors";
import type { ApiResult } from "@/lib/api/types";

interface GetJsonOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

export async function getJson<T>(
  path: string,
  options: GetJsonOptions = {}
): Promise<ApiResult<T>> {
  const { baseUrl, forceMock } = getApiConfig();
  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Mock mode is forcing local fallback.");
  }
  if (!baseUrl) {
    return makeApiFailure("mock", "missing_base_url", "No API base URL is configured.");
  }

  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? 3500;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const signal = options.signal ?? controller.signal;

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store",
      signal
    });

    if (response.status === 401) {
      return makeApiFailure("backend", "unauthorized", "Authentication is required for this endpoint.", 401);
    }
    if (response.status === 404) {
      return makeApiFailure("unsupported", "not_found", "Endpoint not found.", 404);
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
      const data = (await response.json()) as T;
      return {
        ok: true,
        data,
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_json", "Backend returned invalid JSON.", response.status);
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return makeApiFailure("offline", "timeout", "Backend request timed out.");
    }
    return makeApiFailure("offline", "network_error", "Backend is offline or unreachable.");
  } finally {
    clearTimeout(timeoutId);
  }
}
