import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { fetchAdaptiveQuestionQueue } from "@/lib/api/study";

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

describe("adaptive question queue API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("maps ready attempt-aware questions and preserves backend order", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify(adaptiveQueuePayload()), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchAdaptiveQuestionQueue("study-block:topic-1:doc-1:0", 5);

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/study/blocks/study-block%3Atopic-1%3Adoc-1%3A0/questions/next?limit=5",
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
    expect(result.data.queue_status).toBe("ready");
    expect(result.data.mode).toBe("attempt_aware");
    expect(result.data.items.map((item) => item.question_id)).toEqual([
      "question:weak-first",
      "question:new-second"
    ]);
  });

  it("normalizes away unsafe internal fields from successful payloads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...adaptiveQueuePayload(),
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            score: 10,
            priority_rank: 1,
            adaptive_bucket: "weak",
            items: [
              {
                ...adaptiveQueuePayload().items[0],
                correct_answer: "A",
                rationale: "HIDDEN-RATIONALE",
                mastery_state: "temporarily_mastered"
              }
            ]
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchAdaptiveQuestionQueue("block-1", 5);

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    const dumped = JSON.stringify(result.data);
    expect(result.data.items_count).toBe(1);
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("correct_answer");
    expect(dumped).not.toContain("HIDDEN-RATIONALE");
    expect(dumped).not.toContain("priority_rank");
    expect(dumped).not.toContain("adaptive_bucket");
    expect(dumped).not.toContain("mastery_state");
    expect(dumped).not.toContain("score");
  });

  it("maps not-ready queues to the existing cautious state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            block_id: "block-1",
            queue_status: "not_ready",
            mode: "attempt_aware",
            items_count: 0,
            items: [],
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchAdaptiveQuestionQueue("block-1", 5);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("not_ready");
      expect(result.error.message).toBe("As questões ainda não estão prontas para este bloco.");
    }
  });

  it("rejects malformed limits before fetching", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchAdaptiveQuestionQueue("block-1", 99);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("validation_error");
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it.each([
    [401, "auth_required"],
    [403, "auth_required"],
    [404, "not_found"],
    [422, "validation_error"],
    [502, "backend_offline"],
    [503, "missing_base_url"]
  ])("maps HTTP %i to %s", async (status, code) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchAdaptiveQuestionQueue("block-1", 5);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe(code);
    }
  });

  it("maps invalid backend shapes to invalid_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ queue_status: "ready", source: "user_scope" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const result = await fetchAdaptiveQuestionQueue("block-1", 5);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("invalid_response");
    }
  });

  it("does not read real queue data in mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchAdaptiveQuestionQueue("block-1", 5);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("mock_mode");
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
