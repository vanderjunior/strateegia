import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/study/review/next/route";

describe("next review block same-origin proxy route", () => {
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

  it("targets backend next review endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          review_status: "ready",
          review_id: "review:prepared_materials:3:3",
          basis: "prepared_materials",
          materials_count: 3,
          blocks_count: 3,
          estimated_minutes: 15,
          title: "Revisão acumulada",
          summary: { status: "ready", items: [] },
          questions: { status: "ready", items_count: 3 },
          reinforcement: { status: "needs_review", weak_topics_count: 0, items: [] },
          actions: [],
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/study/review/next", {
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" }
      })
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/review/next",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("sanitizes malicious top-level, nested, and action fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            review_status: "ready",
            review_id: "review:prepared_materials:3:3",
            basis: "prepared_materials",
            materials_count: 3,
            blocks_count: 3,
            estimated_minutes: 15,
            title: "Revisão acumulada",
            summary: {
              status: "ready",
              items: [
                {
                  title: "Atos administrativos",
                  message: "Revise Atos administrativos.",
                  topic_label: "Direito Administrativo",
                  subtopic_label: "Atos administrativos",
                  raw_text: "RAW-SHOULD-NOT-LEAK",
                  section_body: "SECTION-SHOULD-NOT-LEAK"
                },
                {
                  title: "storage_path=/Users/private",
                  message: "answer_key SHOULD-NOT-LEAK",
                  topic_label: "token topic",
                  subtopic_label: "gabarito privado"
                }
              ],
              chunks: [{ body: "CHUNK-SHOULD-NOT-LEAK" }]
            },
            questions: {
              status: "ready",
              items_count: 3,
              answer_key: "ANSWER-SHOULD-NOT-LEAK",
              correct_answer: "CORRECT-SHOULD-NOT-LEAK"
            },
            reinforcement: {
              status: "needs_review",
              weak_topics_count: 0,
              items: [
                {
                  topic_label: "Direito Administrativo",
                  subtopic_label: "Atos administrativos",
                  message: "Revise com calma.",
                  score: 99
                },
                {
                  topic_label: "password_hash",
                  subtopic_label: "correct_alternative",
                  message: "storage_path=/Users/private"
                }
              ],
              progress: { done: true }
            },
            actions: [
              { label: "Abrir revisão", href: "/study/review/review:prepared_materials:3:3" },
              { label: "token action", href: "https://evil.example" }
            ],
            source: "user_scope",
            raw_text: "RAW-SHOULD-NOT-LEAK",
            extracted_text: "EXTRACTED-SHOULD-NOT-LEAK",
            storage_path: "/Users/private/aula.md",
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            progress_payload: "PROGRESS-SHOULD-NOT-LEAK",
            attempt_payload: "ATTEMPT-SHOULD-NOT-LEAK",
            internal_trace: "TRACE-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/study/review/next", { method: "GET" }));
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      review_status: "ready",
      review_id: "review:prepared_materials:3:3",
      basis: "prepared_materials",
      materials_count: 3,
      blocks_count: 3,
      estimated_minutes: 15,
      title: "Revisão acumulada",
      summary: {
        status: "ready",
        items: [
          {
            title: "Atos administrativos",
            message: "Revise Atos administrativos.",
            topic_label: "Direito Administrativo",
            subtopic_label: "Atos administrativos"
          },
          {
            title: "Ponto para revisar",
            message: "Revise os pontos principais dos materiais preparados.",
            topic_label: null,
            subtopic_label: null
          }
        ]
      },
      questions: { status: "ready", items_count: 3 },
      reinforcement: {
        status: "needs_review",
        weak_topics_count: 0,
        items: [
          {
            topic_label: "Direito Administrativo",
            subtopic_label: "Atos administrativos",
            message: "Revise com calma."
          },
          {
            topic_label: null,
            subtopic_label: null,
            message: "Ainda não há histórico suficiente para destacar pontos fracos reais."
          }
        ]
      },
      actions: [
        { label: "Abrir revisão", href: "/study/review/review:prepared_materials:3:3" },
        { label: "Abrir revisão", href: "/study" }
      ],
      source: "user_scope"
    });
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("EXTRACTED-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CHUNK-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("SECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("PROGRESS-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("ATTEMPT-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TRACE-SHOULD-NOT-LEAK");
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

    const response = await GET(new Request("http://localhost/api/study/review/next", { method: "GET" }));

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/study/review/next", { method: "GET" }));

    expect(response.status).toBe(503);
  });

  it("returns 502 when backend cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const response = await GET(new Request("http://localhost/api/study/review/next", { method: "GET" }));

    expect(response.status).toBe(502);
  });
});
