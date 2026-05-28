export interface FrontendApiConfig {
  baseUrl: string | null;
  forceMock: boolean;
}

function normalizeBaseUrl(value: string | undefined): string | null {
  const rawValue = value?.trim() ?? "";
  return rawValue ? rawValue.replace(/\/+$/, "") : null;
}

export function getPublicApiBaseUrl(): string | null {
  return normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
}

export function getServerBackendBaseUrl(): string | null {
  return normalizeBaseUrl(process.env.BACKEND_INTERNAL_URL) ?? getPublicApiBaseUrl();
}

export function getUseMockApi(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCK_API === "true";
}

export function getApiConfig(): FrontendApiConfig {
  return {
    baseUrl: getPublicApiBaseUrl(),
    forceMock: getUseMockApi()
  };
}
