import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/materials/[materialId]/edital/analyze/route";

describe("controlled edital analysis same-origin proxy route", () => {
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

  it("targets the controlled backend edital analysis endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          edital_id: "edital:doc-1",
          document_id: "doc-1",
          analysis_status: "analyzed",
          review_state: "ready_for_review",
          topics_count: 3,
          bibliography_count: 2,
          gaps_count: 0,
          warnings_count: 0,
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new Request("http://localhost/api/materials/doc-1/edital/analyze", {
        method: "POST",
        headers: { cookie: "studyflow_session=server-only" }
      }),
      { params: Promise.resolve({ materialId: "doc-1" }) }
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/materials/doc-1/edital/analyze",
      expect.objectContaining({
        method: "POST",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("sanitizes the bounded analysis response before returning it to the browser", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            edital_id: "edital:doc-1",
            document_id: "doc-1",
            analysis_status: "needs_review",
            review_state: "needs_review",
            topics_count: 3,
            bibliography_count: 2,
            gaps_count: 1,
            warnings_count: 4,
            source: "user_scope",
            extracted_text: "RAW-SHOULD-NOT-LEAK",
            raw_text: "RAW-TEXT-SHOULD-NOT-LEAK",
            storage_path: "/Users/private/edital.md",
            evidence: [{ excerpt: "EVIDENCE-SHOULD-NOT-LEAK" }],
            chunks: [{ body: "CHUNK-SHOULD-NOT-LEAK" }],
            sections: [{ body: "SECTION-SHOULD-NOT-LEAK" }],
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            token: "TOKEN-SHOULD-NOT-LEAK",
            password_hash: "HASH-SHOULD-NOT-LEAK",
            worker_trace: "TRACE-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await POST(new Request("http://localhost/api/materials/doc-1/edital/analyze", { method: "POST" }), {
      params: Promise.resolve({ materialId: "doc-1" })
    });
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      edital_id: "edital:doc-1",
      document_id: "doc-1",
      analysis_status: "needs_review",
      review_state: "needs_review",
      topics_count: 3,
      bibliography_count: 2,
      gaps_count: 1,
      warnings_count: 4,
      source: "user_scope"
    });
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("RAW-TEXT-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
    expect(dumped).not.toContain("EVIDENCE-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CHUNK-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("SECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TOKEN-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("HASH-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TRACE-SHOULD-NOT-LEAK");
  });

  it.each([401, 403, 404, 422])("passes through backend status %i", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Backend response." }), {
          status,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const response = await POST(new Request("http://localhost/api/materials/doc-1/edital/analyze", { method: "POST" }), {
      params: Promise.resolve({ materialId: "doc-1" })
    });

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await POST(new Request("http://localhost/api/materials/doc-1/edital/analyze", { method: "POST" }), {
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

    const response = await POST(new Request("http://localhost/api/materials/doc-1/edital/analyze", { method: "POST" }), {
      params: Promise.resolve({ materialId: "doc-1" })
    });

    expect(response.status).toBe(502);
  });
});
