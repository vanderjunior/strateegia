import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/study/session/next/route";

describe("next study session same-origin proxy route", () => {
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

  it("targets the backend next study session endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          session_status: "ready",
          session_id: "study-session:doc-1",
          document_id: "doc-1",
          material_title: "Aula",
          material_type: "study_material",
          summary_status: "ready",
          estimated_minutes: 5,
          sections_count: 1,
          items: [],
          next_actions: [{ label: "Abrir material", href: "/materials/doc-1" }],
          message: "Comece por este material preparado.",
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/study/session/next", {
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" }
      })
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/session/next",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("sanitizes malicious extra fields before returning data to the browser", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            session_status: "ready",
            session_id: "study-session:doc-1",
            document_id: "doc-1",
            material_title: "Aula segura",
            material_type: "study_material",
            summary_status: "ready",
            estimated_minutes: 5,
            sections_count: 1,
            items: [
              {
                section_id: "section-1",
                title: "Atos administrativos",
                summary: "Resumo em preparação para esta seção.",
                key_points: ["Atos administrativos", "storage_path=/Users/private"],
                estimated_minutes: 5,
                status: "ready",
                raw_text: "RAW-SHOULD-NOT-LEAK",
                body: "BODY-SHOULD-NOT-LEAK"
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
            next_actions: [
              { label: "Abrir material", href: "/materials/doc-1" },
              { label: "token action", href: "https://evil.example" }
            ],
            message: "Comece por este material preparado.",
            source: "user_scope",
            extracted_text: "RAW-SHOULD-NOT-LEAK",
            chunks: [{ body: "CHUNK-SHOULD-NOT-LEAK" }],
            sections: [{ body: "SECTION-SHOULD-NOT-LEAK" }],
            storage_path: "/Users/private/aula.md",
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            token: "TOKEN-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/study/session/next", { method: "GET" }));
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      session_status: "ready",
      session_id: "study-session:doc-1",
      document_id: "doc-1",
      material_title: "Aula segura",
      material_type: "study_material",
      summary_status: "ready",
      estimated_minutes: 5,
      sections_count: 1,
      items: [
        {
          section_id: "section-1",
          title: "Atos administrativos",
          summary: "Resumo em preparação para esta seção.",
          key_points: ["Atos administrativos"],
          estimated_minutes: 5,
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
      next_actions: [
        { label: "Abrir material", href: "/materials/doc-1" },
        { label: "Ver materiais", href: "/materials" }
      ],
      message: "Comece por este material preparado.",
      source: "user_scope"
    });
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CHUNK-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("SECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TOKEN-SHOULD-NOT-LEAK");
  });

  it.each([401, 403])("passes through backend auth status %i", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Backend response." }), {
          status,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const response = await GET(new Request("http://localhost/api/study/session/next", { method: "GET" }));

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/study/session/next", { method: "GET" }));

    expect(response.status).toBe(503);
  });

  it("returns 502 when backend cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const response = await GET(new Request("http://localhost/api/study/session/next", { method: "GET" }));

    expect(response.status).toBe(502);
  });
});
