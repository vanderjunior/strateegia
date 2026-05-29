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
      new Response(JSON.stringify({ metadata: { document_id: "doc-1" } }), {
        status: 201,
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

    expect(response.status).toBe(201);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/materials/upload",
      expect.objectContaining({
        method: "POST",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("returns a bounded upload response and strips raw content and storage fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            metadata: {
              document_id: "doc-1",
              user_id: "user-1",
              filename: "material.txt",
              original_filename: "../../material.txt",
              content_type: "text/plain",
              size_bytes: 18,
              storage_path: "/Users/private/data/uploads/user-1/material.txt",
              status: "extracted",
              extraction_status: "extracted",
              created_at: "2026-05-28T00:00:00Z",
              updated_at: "2026-05-28T00:01:00Z",
              metadata: {
                raw_text: "RAW-METADATA-SHOULD-NOT-LEAK",
                base64: "BASE64-SHOULD-NOT-LEAK"
              }
            },
            extracted_text: "RAW-SHOULD-NOT-LEAK",
            raw_text: "RAW-TEXT-SHOULD-NOT-LEAK",
            base64: "BASE64-SHOULD-NOT-LEAK",
            chunks: [{ body: "CHUNK-SHOULD-NOT-LEAK" }],
            sections: [{ body: "SECTION-SHOULD-NOT-LEAK" }],
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            token: "TOKEN-SHOULD-NOT-LEAK"
          }),
          { status: 201, headers: { "content-type": "application/json" } }
        )
      )
    );

    const formData = new FormData();
    formData.append("file", new File(["conteudo"], "material.txt", { type: "text/plain" }));

    const response = await POST({
      headers: new Headers({ cookie: "studyflow_session=server-only" }),
      formData: async () => formData
    } as unknown as Request);
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(201);
    expect(payload).toEqual({
      metadata: {
        document_id: "doc-1",
        filename: "material.txt",
        original_filename: "../../material.txt",
        content_type: "text/plain",
        size_bytes: 18,
        status: "extracted",
        extraction_status: "extracted",
        created_at: "2026-05-28T00:00:00Z",
        updated_at: "2026-05-28T00:01:00Z"
      },
      message: "Material recebido para validação.",
      source: "user_scope"
    });
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("RAW-TEXT-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("RAW-METADATA-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("BASE64-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CHUNK-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("SECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TOKEN-SHOULD-NOT-LEAK");
  });

  it.each([401, 403, 404, 413, 415, 422])("preserves backend error status %i", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Backend error." }), {
          status,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const formData = new FormData();
    formData.append("file", new File(["conteudo"], "material.txt", { type: "text/plain" }));

    const response = await POST({
      headers: new Headers({ cookie: "studyflow_session=server-only" }),
      formData: async () => formData
    } as unknown as Request);

    expect(response.status).toBe(status);
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
