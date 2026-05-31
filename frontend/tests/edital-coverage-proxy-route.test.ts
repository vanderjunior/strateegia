import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/editais/[editalId]/coverage/route";

describe("edital coverage same-origin proxy route", () => {
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

  it("targets the backend edital coverage endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          edital_id: "edital-user-1",
          analysis_status: "analyzed",
          coverage_status: "partial",
          topics_count: 1,
          subtopics_count: 3,
          covered_subtopics_count: 1,
          partial_subtopics_count: 1,
          uncovered_subtopics_count: 1,
          out_of_scope_materials_count: 0,
          materials_considered_count: 1,
          items: [],
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/editais/edital-user-1/coverage", {
        headers: { cookie: "studyflow_session=server-only" }
      }),
      { params: Promise.resolve({ editalId: "edital-user-1" }) }
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/editais/edital-user-1/coverage",
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
          analysis_status: "not_ready",
          coverage_status: "not_ready",
          topics_count: 0,
          subtopics_count: 0,
          covered_subtopics_count: 0,
          partial_subtopics_count: 0,
          uncovered_subtopics_count: 0,
          out_of_scope_materials_count: 0,
          materials_considered_count: 0,
          items: [],
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(new Request("http://localhost/api/editais/edital%3Adoc-1/coverage"), {
      params: Promise.resolve({ editalId: "edital%3Adoc-1" })
    });

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/editais/edital%3Adoc-1/coverage",
      expect.objectContaining({
        method: "GET",
        cache: "no-store"
      })
    );
  });

  it("sanitizes top-level coverage fields and nested item fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            edital_id: "edital-user-1",
            analysis_status: "analyzed",
            coverage_status: "partial",
            topics_count: 1,
            subtopics_count: 3,
            covered_subtopics_count: 1,
            partial_subtopics_count: 1,
            uncovered_subtopics_count: 1,
            out_of_scope_materials_count: 2,
            materials_considered_count: 1,
            items: [
              {
                topic_id: "topic-1",
                label: "Lingua Portuguesa",
                subtopics_count: 3,
                covered_count: 1,
                partial_count: 1,
                uncovered_count: 1,
                status: "partial",
                evidence: "EVIDENCE-SHOULD-NOT-LEAK",
                raw_text: "RAW-TEXT-SHOULD-NOT-LEAK"
              }
            ],
            source: "user_scope",
            raw_edital_text: "RAW-EDITAL-SHOULD-NOT-LEAK",
            extracted_text: "EXTRACTED-SHOULD-NOT-LEAK",
            chunks: [{ body: "CHUNK-SHOULD-NOT-LEAK" }],
            sections: [{ body: "SECTION-SHOULD-NOT-LEAK" }],
            storage_path: "/Users/private/edital.md",
            token: "TOKEN-SHOULD-NOT-LEAK",
            password_hash: "HASH-SHOULD-NOT-LEAK",
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            progress: { applied: true },
            worker_trace: "TRACE-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/editais/edital-user-1/coverage"), {
      params: Promise.resolve({ editalId: "edital-user-1" })
    });
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      edital_id: "edital-user-1",
      analysis_status: "analyzed",
      coverage_status: "partial",
      topics_count: 1,
      subtopics_count: 3,
      covered_subtopics_count: 1,
      partial_subtopics_count: 1,
      uncovered_subtopics_count: 1,
      out_of_scope_materials_count: 2,
      materials_considered_count: 1,
      items: [
        {
          topic_id: "topic-1",
          label: "Lingua Portuguesa",
          subtopics_count: 3,
          covered_count: 1,
          partial_count: 1,
          uncovered_count: 1,
          status: "partial"
        }
      ],
      source: "user_scope"
    });
    expect(dumped).not.toContain("RAW-EDITAL-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("RAW-TEXT-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("EXTRACTED-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CHUNK-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("SECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("EVIDENCE-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
    expect(dumped).not.toContain("TOKEN-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("HASH-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("progress");
    expect(dumped).not.toContain("TRACE-SHOULD-NOT-LEAK");
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

    const response = await GET(new Request("http://localhost/api/editais/edital-user-1/coverage"), {
      params: Promise.resolve({ editalId: "edital-user-1" })
    });

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/editais/edital-user-1/coverage"), {
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

    const response = await GET(new Request("http://localhost/api/editais/edital-user-1/coverage"), {
      params: Promise.resolve({ editalId: "edital-user-1" })
    });

    expect(response.status).toBe(502);
  });
});
