import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { reviewStudyBlockQuestionAnswer } from "@/lib/api/study";

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

describe("answer review API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("maps reviewed/ungraded bounded response and strips extra unsafe fields", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          ...reviewedPayload(),
          answer_key: "ANSWER-SHOULD-NOT-LEAK",
          correct_answer: "CORRECT-SHOULD-NOT-LEAK",
          gabarito: "GABARITO-SHOULD-NOT-LEAK",
          correction: "CORRECTION-SHOULD-NOT-LEAK",
          score: 10,
          raw_text: "RAW-SHOULD-NOT-LEAK",
          storage_path: "/Users/private",
          token: "TOKEN-SHOULD-NOT-LEAK",
          progress: { done: true }
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const result = await reviewStudyBlockQuestionAnswer(
      "study-block:topic-1:doc-1:0",
      "question:study-block:topic-1:doc-1:0:0",
      { answer: "Minha resposta", answer_format: "text" }
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/study/blocks/study-block%3Atopic-1%3Adoc-1%3A0/questions/question%3Astudy-block%3Atopic-1%3Adoc-1%3A0%3A0/answer/review",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        cache: "no-store",
        body: JSON.stringify({ answer: "Minha resposta", answer_format: "text" })
      })
    );
    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data).toEqual(reviewedPayload());
    const dumped = JSON.stringify(result.data);
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CORRECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("/Users/");
    expect(dumped).not.toContain("TOKEN-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("progress");
  });

  it("maps needs_review response as bounded success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...reviewedPayload(),
            review_status: "needs_review",
            result: "needs_review",
            reinforcement: {
              topic_label: null,
              subtopic_label: null,
              message: "Revise o resumo do bloco antes de avançar.",
              suggested_action: "revisit_block"
            }
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await reviewStudyBlockQuestionAnswer("block-1", "question-1", {
      answer: "Resposta",
      answer_format: "choice"
    });

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.review_status).toBe("needs_review");
    expect(result.data.result).toBe("needs_review");
    expect(result.data.reinforcement.suggested_action).toBe("revisit_block");
  });

  it.each([
    [401, "auth_required", "Entre para revisar sua resposta."],
    [403, "auth_required", "Entre para revisar sua resposta."],
    [404, "not_found", "Questão ou bloco de estudo não encontrado."],
    [422, "validation_error", "Revise sua resposta antes de enviar."],
    [502, "backend_offline", "Não foi possível revisar sua resposta agora."],
    [503, "missing_base_url", "A revisão da resposta não está configurada neste ambiente."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await reviewStudyBlockQuestionAnswer("block-1", "question-1", {
      answer: "Resposta",
      answer_format: "text"
    });

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("maps backend network errors to backend_offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const result = await reviewStudyBlockQuestionAnswer("block-1", "question-1", {
      answer: "Resposta",
      answer_format: "text"
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("backend_offline");
    }
  });

  it("maps missing local config to unsupported without fetching", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "",
      forceMock: false
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await reviewStudyBlockQuestionAnswer("block-1", "question-1", {
      answer: "Resposta",
      answer_format: "text"
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("missing_base_url");
      expect(result.source).toBe("unsupported");
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("does not review real answers in mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await reviewStudyBlockQuestionAnswer("block-1", "question-1", {
      answer: "Resposta",
      answer_format: "text"
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("mock_mode");
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("maps invalid answer format before fetching", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await reviewStudyBlockQuestionAnswer("block-1", "question-1", {
      answer: "Resposta",
      answer_format: "unsupported" as "text"
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("validation_error");
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("maps invalid JSON and invalid shapes to invalid_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{", { status: 200, headers: { "content-type": "application/json" } }))
    );
    const invalidJson = await reviewStudyBlockQuestionAnswer("block-1", "question-1", {
      answer: "Resposta",
      answer_format: "text"
    });
    expect(invalidJson.ok).toBe(false);
    if (!invalidJson.ok) {
      expect(invalidJson.error.code).toBe("invalid_response");
    }

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ review_status: "reviewed", source: "user_scope" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );
    const invalidShape = await reviewStudyBlockQuestionAnswer("block-1", "question-1", {
      answer: "Resposta",
      answer_format: "text"
    });
    expect(invalidShape.ok).toBe(false);
    if (!invalidShape.ok) {
      expect(invalidShape.error.code).toBe("invalid_response");
    }
  });

  it.each([
    ["not_ready", "backend", "not_ready"],
    ["unsupported", "unsupported", "missing_base_url"]
  ])("maps review_status %s to failure", async (reviewStatus, source, code) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...reviewedPayload(),
            review_status: reviewStatus,
            result: "needs_review"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await reviewStudyBlockQuestionAnswer("block-1", "question-1", {
      answer: "Resposta",
      answer_format: "text"
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.source).toBe(source);
      expect(result.error.code).toBe(code);
    }
  });
});
