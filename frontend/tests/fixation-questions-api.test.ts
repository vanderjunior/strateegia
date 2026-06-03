import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { fetchStudyBlockQuestions } from "@/lib/api/study";

function readyQuestionsPayload() {
  return {
    block_id: "study-block:topic-1:doc-1:0",
    question_status: "ready",
    mode: "review_only",
    items: [
      {
        question_id: "question:study-block:topic-1:doc-1:0:0",
        type: "multiple_choice",
        prompt: "Considerando o tema Direito Administrativo, escolha uma alternativa para orientar sua revisão de Atos administrativos.",
        alternatives: [
          { id: "A", text: "Revisar Atos administrativos." },
          { id: "B", text: "Relacionar Direito Administrativo ao resumo do bloco." },
          { id: "C", text: "Identificar pontos principais de Atos administrativos." },
          { id: "D", text: "Retomar Direito Administrativo no material estudado." },
          { id: "E", text: "Comparar Atos administrativos com os demais pontos do bloco." }
        ],
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

describe("fixation questions API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("maps ready bounded review-only questions", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify(readyQuestionsPayload()), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchStudyBlockQuestions("study-block:topic-1:doc-1:0");

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/study/blocks/study-block%3Atopic-1%3Adoc-1%3A0/questions",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
        cache: "no-store"
      })
    );
    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.question_status).toBe("ready");
    expect(result.data.mode).toBe("review_only");
    expect(result.data.items[0].type).toBe("multiple_choice");
    expect(result.data.items[0].alternatives.map((alternative) => alternative.id)).toEqual(["A", "B", "C", "D", "E"]);
    expect(JSON.stringify(result.data)).not.toContain("answer_key");
    expect(JSON.stringify(result.data)).not.toContain("gabarito");
    expect(JSON.stringify(result.data)).not.toContain("correction");
    expect(JSON.stringify(result.data)).not.toContain("storage_path");
    expect(JSON.stringify(result.data)).not.toContain("token");
  });

  it("maps needs-review question candidates as bounded success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...readyQuestionsPayload(),
            question_status: "needs_review",
            items: [
              {
                ...readyQuestionsPayload().items[0],
                topic_label: null,
                subtopic_label: null,
                status: "needs_review"
              }
            ],
            warnings_count: 1
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchStudyBlockQuestions("block-1");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.question_status).toBe("needs_review");
    expect(result.data.items[0].status).toBe("needs_review");
    expect(result.data.warnings_count).toBe(1);
  });

  it("maps not-ready question data to a not_ready result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            block_id: "study-block:not-ready:doc-1:0",
            question_status: "not_ready",
            mode: "review_only",
            items: [],
            warnings_count: 0,
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchStudyBlockQuestions("study-block:not-ready:doc-1:0");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected not-ready failure");
    }
    expect(result.error.code).toBe("not_ready");
    expect(result.error.message).toBe("As questões ainda não estão prontas para este bloco.");
  });

  it.each([
    [401, "auth_required", "Entre para ver as questões deste bloco."],
    [403, "auth_required", "Entre para ver as questões deste bloco."],
    [404, "not_found", "Bloco de estudo não encontrado."],
    [502, "backend_offline", "Não foi possível carregar as questões agora."],
    [503, "missing_base_url", "As questões deste bloco não estão configuradas neste ambiente."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchStudyBlockQuestions("block-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("maps missing local config to unsupported without fetching", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "",
      forceMock: false
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchStudyBlockQuestions("block-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("missing_base_url");
    expect(result.source).toBe("unsupported");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("does not read real questions in mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchStudyBlockQuestions("block-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("mock_mode");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("maps invalid JSON and invalid shapes to invalid_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{", { status: 200, headers: { "content-type": "application/json" } }))
    );
    const invalidJson = await fetchStudyBlockQuestions("block-1");
    expect(invalidJson.ok).toBe(false);
    if (!invalidJson.ok) {
      expect(invalidJson.error.code).toBe("invalid_response");
    }

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ question_status: "ready", source: "user_scope" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );
    const invalidShape = await fetchStudyBlockQuestions("block-1");
    expect(invalidShape.ok).toBe(false);
    if (!invalidShape.ok) {
      expect(invalidShape.error.code).toBe("invalid_response");
    }

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...readyQuestionsPayload(),
            mode: "answer_review",
            answer_key: "ANSWER-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );
    const invalidMode = await fetchStudyBlockQuestions("block-1");
    expect(invalidMode.ok).toBe(false);
    if (!invalidMode.ok) {
      expect(invalidMode.error.code).toBe("invalid_response");
    }
  });

  it("maps network failures to backend_offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const result = await fetchStudyBlockQuestions("block-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("backend_offline");
    expect(result.error.message).toBe("Não foi possível carregar as questões agora.");
  });
});
