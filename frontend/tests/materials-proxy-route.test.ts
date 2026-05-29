import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { GET } from "@/app/api/materials/route";

describe("materials same-origin proxy route", () => {
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

  it("targets the dedicated backend materials endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          items: [],
          count: 0,
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/materials", {
        headers: { cookie: "studyflow_session=server-only" }
      })
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/materials",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("sanitizes the backend bounded list before returning it to the browser", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            items: [
              {
                document_id: "doc-1",
                display_filename: "roteiro.pdf",
                content_type: "pdf",
                material_type: "previous_exam",
                created_at: "2026-05-27T00:00:00Z",
                updated_at: "2026-05-27T00:05:00Z",
                processing_status: "ready_for_review",
                extraction_status: "textual_pdf",
                chunk_count: 12,
                section_count: 4,
                review_state: "ready_for_review",
                warnings_count: 0,
                latest_pipeline_status: "metadata_ready",
                extracted_text: "RAW-SHOULD-NOT-LEAK",
                storage_path: "/Users/private/upload.pdf",
                token: "secret"
              }
            ],
            count: 1,
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/materials"));
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      total_materials: 1,
      processed_count: 1,
      pending_count: 0,
      ocr_required_count: 0,
      items: [
        {
          document_id: "doc-1",
          display_filename: "roteiro.pdf",
          content_type: "pdf",
          material_type: "previous_exam",
          status: "ready_for_review",
          uploaded_at: "2026-05-27T00:00:00Z",
          extraction_status: "textual_pdf",
          current_stage: "metadata_ready",
          metadata_status: "ready",
          chunk_count: 12,
          section_count: 4
        }
      ]
    });
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
    expect(dumped).not.toContain("secret");
  });

  it.each([401, 403])("passes through auth status %i", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Authentication required." }), {
          status,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const response = await GET(new Request("http://localhost/api/materials"));

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/materials"));

    expect(response.status).toBe(503);
  });

  it("returns 502 when the backend cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const response = await GET(new Request("http://localhost/api/materials"));

    expect(response.status).toBe(502);
  });
});
