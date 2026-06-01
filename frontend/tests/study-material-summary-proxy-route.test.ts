import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/materials/[materialId]/study/summary/route";

describe("study material summary same-origin proxy route", () => {
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

  it("targets the backend study summary endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          document_id: "doc:with space",
          summary_status: "ready",
          material_type: "study_material",
          title: "Aula",
          sections_count: 1,
          items: [],
          warnings_count: 0,
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/materials/doc%3Awith%20space/study/summary", {
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" }
      }),
      { params: Promise.resolve({ materialId: "doc:with space" }) }
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/materials/doc%3Awith%20space/study/summary",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("sanitizes top-level and item fields before returning data to the browser", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            document_id: "doc-1",
            summary_status: "ready",
            material_type: "study_material",
            title: "Resumo seguro",
            sections_count: 1,
            items: [
              {
                section_id: "section-1",
                title: "Atos administrativos",
                summary: "Resumo em preparação para esta seção.",
                key_points: ["Atos administrativos", "storage_path=/Users/private"],
                estimated_minutes: 8,
                status: "ready",
                raw_text: "RAW-SHOULD-NOT-LEAK",
                body: "BODY-SHOULD-NOT-LEAK",
                storage_path: "/Users/private/aula.md"
              },
              {
                section_id: "section-2",
                title: "token secret",
                summary: "storage_path=/Users/private",
                key_points: ["GABARITO-SHOULD-NOT-LEAK"],
                estimated_minutes: 4,
                status: "surprise"
              }
            ],
            warnings_count: 0,
            source: "user_scope",
            extracted_text: "RAW-SHOULD-NOT-LEAK",
            chunks: [{ body: "CHUNK-SHOULD-NOT-LEAK" }],
            sections: [{ body: "SECTION-SHOULD-NOT-LEAK" }],
            evidence_snippets: ["EVIDENCE-SHOULD-NOT-LEAK"],
            storage_path: "/Users/private/aula.md",
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            token: "TOKEN-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/materials/doc-1/study/summary", { method: "GET" }), {
      params: Promise.resolve({ materialId: "doc-1" })
    });
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      document_id: "doc-1",
      summary_status: "ready",
      material_type: "study_material",
      title: "Resumo seguro",
      sections_count: 1,
      items: [
        {
          section_id: "section-1",
          title: "Atos administrativos",
          summary: "Resumo em preparação para esta seção.",
          key_points: ["Atos administrativos"],
          estimated_minutes: 8,
          status: "ready"
        },
        {
          section_id: "section-2",
          title: "Seção do material",
          summary: "Resumo em preparação para esta seção.",
          key_points: [],
          estimated_minutes: 4,
          status: "needs_review"
        }
      ],
      warnings_count: 0,
      source: "user_scope"
    });
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CHUNK-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("SECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("EVIDENCE-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TOKEN-SHOULD-NOT-LEAK");
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

    const response = await GET(new Request("http://localhost/api/materials/doc-1/study/summary", { method: "GET" }), {
      params: Promise.resolve({ materialId: "doc-1" })
    });

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/materials/doc-1/study/summary", { method: "GET" }), {
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

    const response = await GET(new Request("http://localhost/api/materials/doc-1/study/summary", { method: "GET" }), {
      params: Promise.resolve({ materialId: "doc-1" })
    });

    expect(response.status).toBe(502);
  });
});
