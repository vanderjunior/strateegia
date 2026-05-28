import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/materials/upload/route";

describe("materials upload same-origin proxy route", () => {
  const originalBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const originalInternalUrl = process.env.BACKEND_INTERNAL_URL;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000";
    process.env.BACKEND_INTERNAL_URL = "http://backend:8000";
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
    process.env.BACKEND_INTERNAL_URL = originalInternalUrl;
    vi.unstubAllGlobals();
  });

  it("targets the internal backend URL and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify({ document_id: "doc-1" }), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const formData = new FormData();
    formData.append("file", new File(["conteudo"], "material.txt", { type: "text/plain" }));

    const response = await POST({
      headers: new Headers({ cookie: "studyflow_session=server-only" }),
      formData: async () => formData
    } as unknown as Request);

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/materials/upload",
      expect.objectContaining({
        method: "POST",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("returns 503 when neither backend URL is configured", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await POST(new Request("http://localhost/api/materials/upload", {
      method: "POST",
      body: new FormData()
    }));

    expect(response.status).toBe(503);
  });
});
