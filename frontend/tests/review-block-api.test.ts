import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { fetchNextReviewBlock } from "@/lib/api/study";

function readyReviewPayload() {
  return {
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
        }
      ]
    },
    questions: { status: "ready", items_count: 3 },
    reinforcement: {
      status: "needs_review",
      weak_topics_count: 0,
      items: [
        {
          topic_label: null,
          subtopic_label: null,
          message: "Ainda não há histórico suficiente para destacar pontos fracos reais."
        }
      ]
    },
    actions: [{ label: "Abrir revisão", href: "/study/review/review:prepared_materials:3:3" }],
    source: "user_scope"
  };
}

describe("next review block API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("maps ready bounded review data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify(readyReviewPayload()), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const result = await fetchNextReviewBlock();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.review_status).toBe("ready");
    expect(result.data.basis).toBe("prepared_materials");
    expect(result.data.materials_count).toBe(3);
    expect(JSON.stringify(result.data)).not.toContain("gabarito");
    expect(JSON.stringify(result.data)).not.toContain("answer_key");
    expect(JSON.stringify(result.data)).not.toContain("storage_path");
  });

  it.each(["needs_review", "partial"] as const)("maps %s review data as success", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...readyReviewPayload(),
            review_status: status,
            basis: "study_blocks"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchNextReviewBlock();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.review_status).toBe(status);
    expect(result.data.basis).toBe("study_blocks");
  });

  it("maps not-ready review response to a not_ready result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            review_status: "not_ready",
            review_id: null,
            basis: "prepared_materials",
            materials_count: 0,
            blocks_count: 0,
            estimated_minutes: 0,
            title: "Revisão acumulada",
            summary: { status: "not_ready", items: [] },
            questions: { status: "not_ready", items_count: 0 },
            reinforcement: { status: "not_ready", weak_topics_count: 0, items: [] },
            actions: [],
            message: "Prepare pelo menos 3 materiais de estudo para montar uma revisão acumulada.",
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchNextReviewBlock();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected not-ready failure");
    }
    expect(result.error.code).toBe("not_ready");
    expect(result.error.message).toBe("Prepare pelo menos 3 materiais de estudo para montar uma revisão acumulada.");
  });

  it.each([
    [401, "auth_required", "Entre para ver sua revisão acumulada."],
    [403, "auth_required", "Entre para ver sua revisão acumulada."],
    [502, "backend_offline", "Não foi possível carregar a revisão agora."],
    [503, "missing_base_url", "A revisão acumulada não está configurada neste ambiente."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchNextReviewBlock();

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

    const result = await fetchNextReviewBlock();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("missing_base_url");
    expect(result.source).toBe("unsupported");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("does not read real review in mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchNextReviewBlock();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("mock_mode");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("maps invalid JSON and invalid shape to invalid_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{", { status: 200, headers: { "content-type": "application/json" } }))
    );
    const invalidJson = await fetchNextReviewBlock();
    expect(invalidJson.ok).toBe(false);
    if (!invalidJson.ok) {
      expect(invalidJson.error.code).toBe("invalid_response");
    }

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ review_status: "ready", source: "user_scope" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );
    const invalidShape = await fetchNextReviewBlock();
    expect(invalidShape.ok).toBe(false);
    if (!invalidShape.ok) {
      expect(invalidShape.error.code).toBe("invalid_response");
    }
  });

  it("maps network failures to backend_offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const result = await fetchNextReviewBlock();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("backend_offline");
    expect(result.error.message).toBe("Não foi possível carregar a revisão agora.");
  });
});
