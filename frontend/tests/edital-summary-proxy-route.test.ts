import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/editais/[editalId]/summary/route";

describe("edital summary same-origin proxy route", () => {
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

  it("targets the dedicated backend edital summary endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          edital_id: "edital-user-1",
          document_id: "doc-1",
          title: "Edital analisado da sessão",
          topics_count: 0,
          subtopics_count: 0,
          bibliography_count: 0,
          gaps_count: 0,
          review_state: "unknown",
          coverage_status: "unknown",
          alignment_status: "unknown",
          warnings_count: 0,
          summary: {},
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/editais/edital-user-1/summary", {
        headers: { cookie: "studyflow_session=server-only" }
      }),
      { params: Promise.resolve({ editalId: "edital-user-1" }) }
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/editais/edital-user-1/summary",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("decodes an encoded edital_id route segment before forwarding to backend", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          edital_id: "edital:doc-1",
          document_id: "doc-1",
          title: "Edital recebido",
          analysis_status: "not_ready",
          topics_count: 0,
          subtopics_count: 0,
          bibliography_count: 0,
          gaps_count: 0,
          review_state: "needs_review",
          coverage_status: "unknown",
          alignment_status: "not_available",
          warnings_count: 1,
          summary: {},
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(new Request("http://localhost/api/editais/edital%3Adoc-1/summary"), {
      params: Promise.resolve({ editalId: "edital%3Adoc-1" })
    });

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/editais/edital%3Adoc-1/summary",
      expect.objectContaining({
        method: "GET",
        cache: "no-store"
      })
    );
  });

  it("sanitizes the bounded summary before returning it to the browser", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            edital_id: "edital-user-1",
            document_id: "doc-1",
            title: "Edital analisado da sessão",
            created_at: "2026-05-27T00:00:00Z",
            updated_at: "2026-05-27T00:05:00Z",
            analysis_status: "needs_review",
            topics_count: 12,
            subtopics_count: 42,
            bibliography_count: 8,
            gaps_count: 3,
            review_state: "needs_review",
            coverage_status: "partial",
            alignment_status: "needs_review",
            warnings_count: 2,
            summary: {
              has_topics: true,
              has_subtopics: true,
              has_bibliography: true,
              has_gaps: true,
              needs_review: true,
              raw_topic_excerpt: "TOPIC-SHOULD-NOT-LEAK"
            },
            source: "user_scope",
            raw_edital_text: "RAW-EDITAL-SHOULD-NOT-LEAK",
            extracted_text: "EXTRACTED-SHOULD-NOT-LEAK",
            evidence: [{ excerpt: "EVIDENCE-SHOULD-NOT-LEAK" }],
            bibliography_body: "BIBLIOGRAPHY-SHOULD-NOT-LEAK",
            storage_path: "/Users/private/edital.md",
            token: "secret"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/editais/edital-user-1/summary"), {
      params: Promise.resolve({ editalId: "edital-user-1" })
    });
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      edital_id: "edital-user-1",
      document_id: "doc-1",
      title: "Edital analisado da sessão",
      created_at: "2026-05-27T00:00:00Z",
      updated_at: "2026-05-27T00:05:00Z",
      analysis_status: "needs_review",
      topics_count: 12,
      subtopics_count: 42,
      bibliography_count: 8,
      gaps_count: 3,
      review_state: "needs_review",
      coverage_status: "partial",
      alignment_status: "needs_review",
      warnings_count: 2,
      summary: {
        has_topics: true,
        has_subtopics: true,
        has_bibliography: true,
        has_gaps: true,
        needs_review: true
      },
      source: "user_scope"
    });
    expect(dumped).not.toContain("RAW-EDITAL-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("EXTRACTED-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("EVIDENCE-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("BIBLIOGRAPHY-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TOPIC-SHOULD-NOT-LEAK");
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

    const response = await GET(new Request("http://localhost/api/editais/edital-user-1/summary"), {
      params: Promise.resolve({ editalId: "edital-user-1" })
    });

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/editais/edital-user-1/summary"), {
      params: Promise.resolve({ editalId: "edital-user-1" })
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

    const response = await GET(new Request("http://localhost/api/editais/edital-user-1/summary"), {
      params: Promise.resolve({ editalId: "edital-user-1" })
    });

    expect(response.status).toBe(502);
  });
});
