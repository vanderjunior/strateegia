import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/materials/[materialId]/pipeline/summary/route";

describe("pipeline summary same-origin proxy route", () => {
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

  it("targets the dedicated backend pipeline summary endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          document_id: "doc-1",
          status: "ready_for_review",
          steps: [],
          steps_count: 0,
          has_ocr_warning: false,
          ready_for_review: true,
          section_count: 0,
          chunk_count: 0,
          warnings_count: 0,
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/materials/doc-1/pipeline/summary", {
        headers: { cookie: "studyflow_session=server-only" }
      }),
      { params: Promise.resolve({ materialId: "doc-1" }) }
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/materials/doc-1/pipeline/summary",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("sanitizes the bounded pipeline summary before returning it to the browser", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            document_id: "doc-1",
            status: "ready_for_review",
            steps: [
              {
                key: "uploaded",
                label: "Enviado",
                state: "done",
                warnings_count: 0,
                worker_trace: "WORKER-SHOULD-NOT-LEAK"
              }
            ],
            steps_count: 1,
            has_ocr_warning: false,
            ready_for_review: true,
            section_count: 4,
            chunk_count: 12,
            warnings_count: 0,
            source: "user_scope",
            extracted_text: "RAW-SHOULD-NOT-LEAK",
            raw_chunks: [{ body: "CHUNK-SHOULD-NOT-LEAK" }],
            raw_sections: [{ body: "SECTION-SHOULD-NOT-LEAK" }],
            storage_path: "/Users/private/upload.pdf",
            job_trace: "JOB-SHOULD-NOT-LEAK",
            token: "secret"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/materials/doc-1/pipeline/summary"), {
      params: Promise.resolve({ materialId: "doc-1" })
    });
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      document_id: "doc-1",
      status: "ready_for_review",
      steps: [
        {
          key: "uploaded",
          label: "Enviado",
          state: "done",
          warnings_count: 0
        }
      ],
      steps_count: 1,
      has_ocr_warning: false,
      ready_for_review: true,
      section_count: 4,
      chunk_count: 12,
      warnings_count: 0,
      source: "user_scope"
    });
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CHUNK-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("SECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("WORKER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("JOB-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
    expect(dumped).not.toContain("secret");
  });

  it.each([401, 403, 404])("passes through backend status %i", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Backend response." }), {
          status,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const response = await GET(new Request("http://localhost/api/materials/doc-1/pipeline/summary"), {
      params: Promise.resolve({ materialId: "doc-1" })
    });

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/materials/doc-1/pipeline/summary"), {
      params: Promise.resolve({ materialId: "doc-1" })
    });

    expect(response.status).toBe(503);
  });

  it("returns 502 when the backend cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const response = await GET(new Request("http://localhost/api/materials/doc-1/pipeline/summary"), {
      params: Promise.resolve({ materialId: "doc-1" })
    });

    expect(response.status).toBe(502);
  });
});
