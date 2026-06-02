import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/study/blocks/[blockId]/route";

function readyDetailPayload() {
  return {
    block_id: "study-block:topic-1:doc-1:0",
    detail_status: "ready",
    title: "Atos administrativos",
    topic_id: "topic-1",
    topic_label: "Direito Administrativo",
    subtopic_id: "subtopic-1",
    subtopic_label: "Atos administrativos",
    material_id: "doc-1",
    material_title: "Aula preparada",
    summary_status: "ready",
    estimated_minutes: 5,
    sections: [
      {
        section_id: "section-1",
        title: "Atos administrativos",
        summary: "Resumo em preparação para esta seção.",
        key_points: ["Atos administrativos"],
        estimated_minutes: 5,
        status: "ready"
      }
    ],
    actions: [
      { label: "Abrir material", href: "/materials/doc-1" },
      { label: "Voltar ao caminho de estudo", href: "/study" }
    ],
    source: "user_scope"
  };
}

describe("study block detail same-origin proxy route", () => {
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

  it("targets backend study block detail endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify(readyDetailPayload()), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const blockId = "study-block:topic-1:doc 1:0";
    const response = await GET(
      new Request("http://localhost/api/study/blocks/study-block%3Atopic-1%3Adoc%201%3A0", {
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" }
      }),
      { params: Promise.resolve({ blockId }) }
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/blocks/study-block%3Atopic-1%3Adoc%201%3A0",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("sanitizes malicious top-level, section, and action fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...readyDetailPayload(),
            sections: [
              {
                section_id: "section-1",
                title: "Atos administrativos",
                summary: "Resumo em preparação para esta seção.",
                key_points: ["Atos administrativos", "storage_path=/Users/private"],
                estimated_minutes: 5,
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
            actions: [
              { label: "Abrir material", href: "/materials/doc-1" },
              { label: "token action", href: "https://evil.example" },
              { label: "cookie", href: "//evil.example" }
            ],
            extracted_text: "RAW-SHOULD-NOT-LEAK",
            chunks: [{ body: "CHUNK-SHOULD-NOT-LEAK" }],
            sections_body: [{ body: "SECTION-SHOULD-NOT-LEAK" }],
            evidence_snippets: ["EVIDENCE-SHOULD-NOT-LEAK"],
            storage_path: "/Users/private/aula.md",
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            token: "TOKEN-SHOULD-NOT-LEAK",
            progress: { done: true },
            worker: "JOB-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      block_id: "study-block:topic-1:doc-1:0",
      detail_status: "ready",
      title: "Atos administrativos",
      topic_id: "topic-1",
      topic_label: "Direito Administrativo",
      subtopic_id: "subtopic-1",
      subtopic_label: "Atos administrativos",
      material_id: "doc-1",
      material_title: "Aula preparada",
      summary_status: "ready",
      estimated_minutes: 5,
      sections: [
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
      actions: [
        { label: "Abrir material", href: "/materials/doc-1" },
        { label: "Voltar ao caminho de estudo", href: "/study" },
        { label: "Voltar ao caminho de estudo", href: "/study" }
      ],
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
    expect(dumped).not.toContain("JOB-SHOULD-NOT-LEAK");
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

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });

    expect(response.status).toBe(503);
  });

  it("returns 502 when backend cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });

    expect(response.status).toBe(502);
  });
});
