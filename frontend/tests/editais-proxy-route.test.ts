import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/editais/route";

describe("editais same-origin proxy route", () => {
  const originalBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000";
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
    vi.unstubAllGlobals();
  });

  it("targets the dedicated backend editais endpoint and forwards cookies server-side", async () => {
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
      new Request("http://localhost/api/editais", {
        headers: { cookie: "studyflow_session=server-only" }
      })
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/editais",
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
                edital_id: "edital:doc-1",
                document_id: "doc-1",
                title: "Edital analisado da sessão",
                created_at: "2026-05-27T00:00:00Z",
                updated_at: "2026-05-27T00:05:00Z",
                topics_count: 12,
                bibliography_count: 8,
                gaps_count: 3,
                review_state: "needs_review",
                coverage_status: "partial",
                alignment_status: "needs_review",
                warnings_count: 2,
                raw_edital_text: "RAW-EDITAL-SHOULD-NOT-LEAK",
                evidence: [{ excerpt: "EVIDENCE-SHOULD-NOT-LEAK" }],
                storage_path: "/Users/private/edital.md",
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

    const response = await GET(new Request("http://localhost/api/editais"));
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      total_editais: 1,
      total_topics: 12,
      total_bibliography_items: 8,
      total_gaps: 3,
      items: [
        {
          edital_id: "edital:doc-1",
          title: "Edital analisado da sessão",
          status: "Análise candidata",
          review_state: "Precisa de conferência",
          topics_count: 12,
          bibliography_count: 8,
          gaps_count: 3,
          coverage_status: "Cobertura parcial",
          latest_document_id: "doc-1"
        }
      ]
    });
    expect(dumped).not.toContain("RAW-EDITAL-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("EVIDENCE-SHOULD-NOT-LEAK");
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

    const response = await GET(new Request("http://localhost/api/editais"));

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;

    const response = await GET(new Request("http://localhost/api/editais"));

    expect(response.status).toBe(503);
  });

  it("returns 502 when the backend cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const response = await GET(new Request("http://localhost/api/editais"));

    expect(response.status).toBe(502);
  });
});
