import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/study/blocks/[blockId]/questions/next/route";

function adaptiveQueuePayload() {
  return {
    block_id: "study-block:topic-1:doc-1:0",
    queue_status: "ready",
    mode: "attempt_aware",
    items_count: 2,
    items: [
      {
        question_id: "question:weak-first",
        type: "multiple_choice",
        prompt: "Qual regra aparece no material?",
        alternatives: [
          { id: "A", text: "Aplicar a regra expressa." },
          { id: "B", text: "Ignorar a regra expressa." }
        ],
        topic_label: "Direito Administrativo",
        subtopic_label: "Atos administrativos",
        difficulty: "basic",
        status: "candidate"
      },
      {
        question_id: "question:new-second",
        type: "true_false",
        prompt: "O material afirma uma condição objetiva.",
        alternatives: [
          { id: "C", text: "Certo" },
          { id: "E", text: "Errado" }
        ],
        topic_label: "Direito Administrativo",
        subtopic_label: null,
        difficulty: "medium",
        status: "candidate"
      }
    ],
    source: "user_scope"
  };
}

describe("adaptive question queue same-origin proxy route", () => {
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

  it("targets backend adaptive queue endpoint, preserves order, and forwards cookies", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify(adaptiveQueuePayload()), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/study/blocks/study-block%3Atopic-1%3Adoc%201%3A0/questions/next?limit=5", {
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" }
      }),
      { params: Promise.resolve({ blockId: "study-block:topic-1:doc 1:0" }) }
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/blocks/study-block%3Atopic-1%3Adoc%201%3A0/questions/next?limit=5",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
    expect(payload.items.map((item: { question_id: string }) => item.question_id)).toEqual([
      "question:weak-first",
      "question:new-second"
    ]);
  });

  it.each(["0", "11", "not-a-number"])("rejects malformed limit %s before backend fetch", async (limit) => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request(`http://localhost/api/study/blocks/block-1/questions/next?limit=${limit}`, { method: "GET" }),
      { params: Promise.resolve({ blockId: "block-1" }) }
    );

    expect(response.status).toBe(422);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("sanitizes unsafe queue, item, and alternative fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...adaptiveQueuePayload(),
            items: [
              {
                ...adaptiveQueuePayload().items[0],
                alternatives: [
                  { id: "A", text: "Certo" },
                  {
                    id: "B",
                    text: "answer_key storage_path /Users/private TOKEN-SHOULD-NOT-LEAK",
                    correct_answer: true
                  }
                ],
                answer_key: "ANSWER-SHOULD-NOT-LEAK",
                correct_answer: "A",
                correct_alternative: "A",
                gabarito: "GABARITO-SHOULD-NOT-LEAK",
                rationale: "RATIONALE-SHOULD-NOT-LEAK",
                priority_rank: 1,
                adaptive_bucket: "weak",
                mastery_state: "temporarily_mastered",
                score: 10,
                raw_text: "RAW-SHOULD-NOT-LEAK",
                storage_path: "/Users/private/aula.md",
                token: "TOKEN-SHOULD-NOT-LEAK",
                password_hash: "HASH-SHOULD-NOT-LEAK",
                internal_trace: "TRACE-SHOULD-NOT-LEAK"
              }
            ],
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            priority_rank: 1,
            adaptive_bucket: "weak",
            internal_trace: "TRACE-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1/questions/next", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload.items).toEqual([
      {
        question_id: "question:weak-first",
        type: "multiple_choice",
        prompt: "Qual regra aparece no material?",
        alternatives: [{ id: "A", text: "Certo" }],
        topic_label: "Direito Administrativo",
        subtopic_label: "Atos administrativos",
        difficulty: "basic",
        status: "candidate"
      }
    ]);
    expect(payload.items_count).toBe(1);
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("RATIONALE-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("priority_rank");
    expect(dumped).not.toContain("adaptive_bucket");
    expect(dumped).not.toContain("mastery_state");
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
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

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1/questions/next", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1/questions/next", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });

    expect(response.status).toBe(503);
  });

  it("returns 502 when backend fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("offline");
      })
    );

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1/questions/next", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });

    expect(response.status).toBe(502);
  });
});
