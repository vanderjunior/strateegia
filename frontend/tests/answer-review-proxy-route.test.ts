import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/study/blocks/[blockId]/questions/[questionId]/answer/review/route";

function reviewedPayload() {
  return {
    block_id: "study-block:topic-1:doc-1:0",
    question_id: "question:study-block:topic-1:doc-1:0:0",
    review_status: "reviewed",
    result: "ungraded",
    feedback: "Compare sua resposta com o resumo do bloco e revise os pontos principais relacionados.",
    reinforcement: {
      topic_label: "Direito Administrativo",
      subtopic_label: "Atos administrativos",
      message: "Revise o resumo do bloco e compare sua resposta com os pontos principais de Atos administrativos.",
      suggested_action: "review_summary"
    },
    source: "user_scope"
  };
}

function requestFor(body: Record<string, unknown>, cookie = "studyflow_session=server-only") {
  return new Request("http://localhost/api/study/blocks/block/questions/question/answer/review", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      cookie
    },
    body: JSON.stringify(body)
  });
}

describe("answer review same-origin proxy route", () => {
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

  it("targets backend answer review endpoint, encodes params, forwards cookies, and whitelists request body", async () => {
    let forwardedInit: RequestInit | undefined;
    const fetchSpy = vi.fn(async (_url: string | URL, init?: RequestInit) => {
      forwardedInit = init;
      return new Response(JSON.stringify(reviewedPayload()), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    });
    vi.stubGlobal("fetch", fetchSpy);

    const blockId = "study-block:topic-1:doc 1:0";
    const questionId = "question:study-block:topic-1:doc 1:0:0";
    const response = await POST(
      requestFor({
        answer: "Minha resposta",
        answer_format: "text",
        answer_key: "ANSWER-SHOULD-NOT-FORWARD",
        correct_answer: "CORRECT-SHOULD-NOT-FORWARD",
        gabarito: "GABARITO-SHOULD-NOT-FORWARD",
        score: 10,
        correction: "CORRECTION-SHOULD-NOT-FORWARD",
        rationale: "RATIONALE-SHOULD-NOT-FORWARD"
      }),
      { params: Promise.resolve({ blockId, questionId }) }
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/blocks/study-block%3Atopic-1%3Adoc%201%3A0/questions/question%3Astudy-block%3Atopic-1%3Adoc%201%3A0%3A0/answer/review",
      expect.objectContaining({
        method: "POST",
        headers: {
          cookie: "studyflow_session=server-only",
          "content-type": "application/json"
        },
        cache: "no-store"
      })
    );
    expect(JSON.parse(String(forwardedInit?.body))).toEqual({
      answer: "Minha resposta",
      answer_format: "text"
    });
  });

  it("decodes already encoded route params before targeting backend", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify(reviewedPayload()), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(requestFor({ answer: "Resposta", answer_format: "text" }), {
      params: Promise.resolve({
        blockId: "study-block%3Atopic-1%3Adoc%201%3A0",
        questionId: "question%3Astudy-block%3Atopic-1%3Adoc%201%3A0%3A0"
      })
    });

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/blocks/study-block%3Atopic-1%3Adoc%201%3A0/questions/question%3Astudy-block%3Atopic-1%3Adoc%201%3A0%3A0/answer/review",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("sanitizes malicious response fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...reviewedPayload(),
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            correct_answer: "CORRECT-SHOULD-NOT-LEAK",
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
            internal_trace: "TRACE-SHOULD-NOT-LEAK",
            reinforcement: {
              ...reviewedPayload().reinforcement,
              answer_key: "ANSWER-SHOULD-NOT-LEAK",
              message: "Revise o resumo do bloco e compare sua resposta com os pontos principais de Atos administrativos.",
              storage_path: "/Users/private"
            }
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await POST(requestFor({ answer: "Resposta", answer_format: "text" }), {
      params: Promise.resolve({ blockId: "block-1", questionId: "question-1" })
    });
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(payload).toEqual(reviewedPayload());
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CORRECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CHUNK-SHOULD-NOT-LEAK");
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

    const response = await POST(requestFor({ answer: "Resposta", answer_format: "text" }), {
      params: Promise.resolve({ blockId: "block-1", questionId: "question-1" })
    });

    expect(response.status).toBe(status);
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await POST(requestFor({ answer: "Resposta", answer_format: "text" }), {
      params: Promise.resolve({ blockId: "block-1", questionId: "question-1" })
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

    const response = await POST(requestFor({ answer: "Resposta", answer_format: "text" }), {
      params: Promise.resolve({ blockId: "block-1", questionId: "question-1" })
    });

    expect(response.status).toBe(502);
  });
});
