import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/study/blocks/[blockId]/questions/route";

function readyQuestionsPayload() {
  return {
    block_id: "study-block:topic-1:doc-1:0",
    question_status: "ready",
    mode: "review_only",
    items: [
      {
        question_id: "question:study-block:topic-1:doc-1:0:0",
        type: "short_answer",
        prompt: "Explique, com suas palavras, o ponto principal relacionado a Atos administrativos.",
        alternatives: [],
        topic_label: "Direito Administrativo",
        subtopic_label: "Atos administrativos",
        difficulty: "basic",
        status: "candidate"
      }
    ],
    warnings_count: 0,
    source: "user_scope"
  };
}

describe("fixation questions same-origin proxy route", () => {
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

  it("targets backend fixation questions endpoint and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify(readyQuestionsPayload()), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const blockId = "study-block:topic-1:doc 1:0";
    const response = await GET(
      new Request("http://localhost/api/study/blocks/study-block%3Atopic-1%3Adoc%201%3A0/questions", {
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" }
      }),
      { params: Promise.resolve({ blockId }) }
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/blocks/study-block%3Atopic-1%3Adoc%201%3A0/questions",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("decodes encoded route params before targeting backend", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify(readyQuestionsPayload()), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(new Request("http://localhost/api/study/blocks/encoded/questions", { method: "GET" }), {
      params: Promise.resolve({ blockId: "study-block%3Atopic-1%3Adoc%201%3A0" })
    });

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/blocks/study-block%3Atopic-1%3Adoc%201%3A0/questions",
      expect.objectContaining({ method: "GET" })
    );
  });

  it("sanitizes malicious top-level, item, and alternative fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...readyQuestionsPayload(),
            items: [
              {
                ...readyQuestionsPayload().items[0],
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
                is_correct: true,
                solution: "SOLUTION-SHOULD-NOT-LEAK",
                rationale: "RATIONALE-SHOULD-NOT-LEAK",
                correction: "CORRECTION-SHOULD-NOT-LEAK",
                score: 10,
                raw_text: "RAW-SHOULD-NOT-LEAK",
                extracted_text: "EXTRACTED-SHOULD-NOT-LEAK",
                chunks: [{ body: "CHUNK-SHOULD-NOT-LEAK" }],
                storage_path: "/Users/private/aula.md",
                token: "TOKEN-SHOULD-NOT-LEAK",
                password_hash: "HASH-SHOULD-NOT-LEAK",
                progress: { done: true },
                worker: "JOB-SHOULD-NOT-LEAK"
              },
              {
                question_id: "question:unsafe:1",
                type: "multiple_choice",
                prompt: "storage_path=/Users/private",
                alternatives: [{ id: "A", text: "Alternativa segura" }],
                difficulty: "hard",
                status: "candidate"
              }
            ],
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            correction: "CORRECTION-SHOULD-NOT-LEAK",
            score: 10,
            evidence_snippets: ["EVIDENCE-SHOULD-NOT-LEAK"],
            storage_path: "/Users/private/aula.md",
            session: "SESSION-SHOULD-NOT-LEAK",
            internal_trace: "TRACE-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1/questions", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual({
      block_id: "study-block:topic-1:doc-1:0",
      question_status: "ready",
      mode: "review_only",
      items: [
        {
          question_id: "question:study-block:topic-1:doc-1:0:0",
          type: "short_answer",
          prompt: "Explique, com suas palavras, o ponto principal relacionado a Atos administrativos.",
          alternatives: [{ id: "A", text: "Certo" }],
          topic_label: "Direito Administrativo",
          subtopic_label: "Atos administrativos",
          difficulty: "basic",
          status: "candidate"
        }
      ],
      warnings_count: 0,
      source: "user_scope"
    });
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CORRECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CHUNK-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("EVIDENCE-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
    expect(dumped).not.toContain("TOKEN-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("HASH-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("SESSION-SHOULD-NOT-LEAK");
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

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1/questions", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1/questions", { method: "GET" }), {
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

    const response = await GET(new Request("http://localhost/api/study/blocks/block-1/questions", { method: "GET" }), {
      params: Promise.resolve({ blockId: "block-1" })
    });

    expect(response.status).toBe(502);
  });
});
