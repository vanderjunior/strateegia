export interface FrontendApiConfig {
  baseUrl: string | null;
  forceMock: boolean;
}

export function getApiConfig(): FrontendApiConfig {
  const rawBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ?? "";
  const forceMock = process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

  return {
    baseUrl: rawBaseUrl ? rawBaseUrl.replace(/\/+$/, "") : null,
    forceMock
  };
}
