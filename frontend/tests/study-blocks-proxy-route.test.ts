import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/study/blocks/route";

describe("study blocks same-origin proxy route", () => {
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

  it("targets backend study blocks endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          blocks_status: "ready",
          scope_status: "connected_to_edital",
          blocks_count: 1,
          estimated_minutes: 5,
          items: [],
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/study/blocks", {
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" }
      })
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/blocks",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("sanitizes malicious top-level, item, and action fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            blocks_status: "ready",
            scope_status: "connected_to_edital",
            blocks_count: 1,
            estimated_minutes: 5,
            items: [
              {
                block_id: "block-1",
                title: "Atos administrativos",
                topic_id: "topic-1",
                topic_label: "Direito Administrativo",
                subtopic_id: "subtopic-1",
                subtopic_label: "Atos administrativos",
                material_id: "doc-1",
                material_title: "Aula segura",
                sections_count: 1,
                summary_status: "ready",
                estimated_minutes: 5,
                status: "ready",
                actions: [
                  { label: "Estudar bloco", href: "/study/blocks/block-1" },
                  { label: "token action", href: "https://evil.example" }
                ],
                extracted_text: "RAW-SHOULD-NOT-LEAK",
                chunks: [{ body: "CHUNK-SHOULD-NOT-LEAK" }],
                sections: [{ body: "SECTION-SHOULD-NOT-LEAK" }],
                storage_path: "/Users/private/aula.md",
                answer_key: "ANSWER-SHOULD-NOT-LEAK",
                gabarito: "GABARITO-SHOULD-NOT-LEAK",
                progress: { done: true },
                worker: "JOB-SHOULD-NOT-LEAK"
              },
              {
                block_id: "block-2",
                title: "storage_path=/Users/private",
                topic_id: "token topic",
                topic_label: "password_hash",
                subtopic_id: "subtopic-2",
                subtopic_label: "gabarito privado",
                material_id: "doc-2",
                material_title: "token material",
                sections_count: 1,
                summary_status: "surprise",
                estimated_minutes: 4,
                status: "surprise",
                actions: [{ label: "cookie", href: "//evil.example" }]
              }
            ],
            message: "Mensagem segura",
            source: "user_scope",
            raw_text: "RAW-SHOULD-NOT-LEAK",
            evidence: "EVIDENCE-SHOULD-NOT-LEAK",
            token: "TOKEN-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/study/blocks", { method: "GET" }));
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      blocks_status: "ready",
      scope_status: "connected_to_edital",
      blocks_count: 1,
      estimated_minutes: 5,
      items: [
        {
          block_id: "block-1",
          title: "Atos administrativos",
          topic_id: "topic-1",
          topic_label: "Direito Administrativo",
          subtopic_id: "subtopic-1",
          subtopic_label: "Atos administrativos",
          material_id: "doc-1",
          material_title: "Aula segura",
          sections_count: 1,
          summary_status: "ready",
          estimated_minutes: 5,
          status: "ready",
          actions: [
            { label: "Estudar bloco", href: "/study/blocks/block-1" },
            { label: "Estudar bloco", href: "/study" }
          ]
        },
        {
          block_id: "block-2",
          title: "Bloco de estudo",
          topic_id: null,
          topic_label: null,
          subtopic_id: "subtopic-2",
          subtopic_label: null,
          material_id: "doc-2",
          material_title: "Material de estudo",
          sections_count: 1,
          summary_status: "not_ready",
          estimated_minutes: 4,
          status: "needs_review",
          actions: [{ label: "Estudar bloco", href: "/study" }]
        }
      ],
      message: "Mensagem segura",
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
    expect(dumped).not.toContain("EVIDENCE-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("JOB-SHOULD-NOT-LEAK");
  });

  it.each([401, 403])("passes through backend auth status %i", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Auth response." }), {
          status,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const response = await GET(new Request("http://localhost/api/study/blocks", { method: "GET" }));

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/study/blocks", { method: "GET" }));

    expect(response.status).toBe(503);
  });

  it("returns 502 when backend cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const response = await GET(new Request("http://localhost/api/study/blocks", { method: "GET" }));

    expect(response.status).toBe(502);
  });
});
