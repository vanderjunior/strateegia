import { afterEach, describe, expect, it } from "vitest";

import {
  getApiConfig,
  getPublicApiBaseUrl,
  getServerBackendBaseUrl,
  getUseMockApi
} from "@/lib/api/config";

describe("frontend API config", () => {
  const originalBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const originalInternalUrl = process.env.BACKEND_INTERNAL_URL;
  const originalUseMock = process.env.NEXT_PUBLIC_USE_MOCK_API;

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
    process.env.BACKEND_INTERNAL_URL = originalInternalUrl;
    process.env.NEXT_PUBLIC_USE_MOCK_API = originalUseMock;
  });

  it("uses the internal backend URL for server-side proxy calls when configured", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/";
    process.env.BACKEND_INTERNAL_URL = "http://backend:8000/";

    expect(getPublicApiBaseUrl()).toBe("http://localhost:8000");
    expect(getServerBackendBaseUrl()).toBe("http://backend:8000");
  });

  it("falls back to the public API base URL when the internal URL is missing", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000/";
    delete process.env.BACKEND_INTERNAL_URL;

    expect(getServerBackendBaseUrl()).toBe("http://127.0.0.1:8000");
  });

  it("returns null for backend URLs when neither value is configured", () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    expect(getPublicApiBaseUrl()).toBeNull();
    expect(getServerBackendBaseUrl()).toBeNull();
  });

  it("keeps the existing public API config and mock flag behavior", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
    process.env.NEXT_PUBLIC_USE_MOCK_API = "true";

    expect(getUseMockApi()).toBe(true);
    expect(getApiConfig()).toEqual({
      baseUrl: "http://localhost:8000",
      forceMock: true
    });
  });
});
