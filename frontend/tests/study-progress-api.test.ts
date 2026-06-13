import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { createStudyProgressEvent, fetchStudyProgressSummary } from "@/lib/api/study";

function eventPayload() {
  return {
    event_id: "study-progress-event:1",
    event_type: "block_marked_studied",
    target_type: "block",
    target_id: "study-block:material:doc-1:0",
    created_at: "2026-06-09T12:00:00+00:00",
    source: "user_scope"
  };
}

function summaryPayload() {
  return {
    progress_status: "ready",
    opened_blocks_count: 1,
    studied_blocks_count: 1,
    prepared_materials_count: 3,
    studied_materials_count: 0,
    review_due: true,
    review_basis: "prepared_materials",
    reviewed_questions_count: 1,
    weak_topics_count: 0,
    source: "user_scope"
  };
}

describe("study progress API wrappers", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("createStudyProgressEvent maps success and sends only allowed request fields", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify(eventPayload()), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const result = await createStudyProgressEvent({
      event_type: "block_marked_studied",
      target_type: "block",
      target_id: "study-block:material:doc-1:0",
      idempotency_key: "mark-doc-1"
    });

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data).toEqual(eventPayload());
    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/study/progress/events",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        cache: "no-store",
        body: JSON.stringify({
          event_type: "block_marked_studied",
          target_type: "block",
          target_id: "study-block:material:doc-1:0",
          idempotency_key: "mark-doc-1"
        })
      })
    );
  });

  it.each([
    [401, "auth_required", "Entre para acompanhar seu progresso."],
    [403, "auth_required", "Entre para acompanhar seu progresso."],
    [422, "invalid_request", "Não foi possível registrar este bloco."],
    [502, "backend_offline", "Não foi possível registrar esta ação agora."],
    [503, "missing_base_url", "O registro de progresso não está configurado neste ambiente."]
  ])("createStudyProgressEvent maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await createStudyProgressEvent({
      event_type: "block_opened",
      target_type: "block",
      target_id: "study-block:material:doc-1:0"
    });

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("createStudyProgressEvent maps missing config, mock mode, network, and invalid response safely", async () => {
    vi.mocked(getApiConfig).mockReturnValue({ baseUrl: "", forceMock: false });
    const missingConfig = await createStudyProgressEvent({
      event_type: "block_opened",
      target_type: "block",
      target_id: "study-block:material:doc-1:0"
    });
    expect(missingConfig.ok).toBe(false);
    if (!missingConfig.ok) {
      expect(missingConfig.error.code).toBe("missing_base_url");
    }

    vi.mocked(getApiConfig).mockReturnValue({ baseUrl: "http://127.0.0.1:8000", forceMock: true });
    const mockMode = await createStudyProgressEvent({
      event_type: "block_opened",
      target_type: "block",
      target_id: "study-block:material:doc-1:0"
    });
    expect(mockMode.ok).toBe(false);
    if (!mockMode.ok) {
      expect(mockMode.error.code).toBe("mock_mode");
    }

    vi.mocked(getApiConfig).mockReturnValue({ baseUrl: "http://127.0.0.1:8000", forceMock: false });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );
    const network = await createStudyProgressEvent({
      event_type: "block_opened",
      target_type: "block",
      target_id: "study-block:material:doc-1:0"
    });
    expect(network.ok).toBe(false);
    if (!network.ok) {
      expect(network.error.code).toBe("backend_offline");
    }

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ event_id: "study-progress-event:1", source: "user_scope" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );
    const invalidShape = await createStudyProgressEvent({
      event_type: "block_opened",
      target_type: "block",
      target_id: "study-block:material:doc-1:0"
    });
    expect(invalidShape.ok).toBe(false);
    if (!invalidShape.ok) {
      expect(invalidShape.error.code).toBe("invalid_response");
    }
  });

  it("fetchStudyProgressSummary maps success and preserves bounded counts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify(summaryPayload()), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const result = await fetchStudyProgressSummary();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data).toEqual(summaryPayload());
    expect(result.data.review_basis).toBe("prepared_materials");
    expect(JSON.stringify(result.data)).not.toContain("gabarito");
    expect(JSON.stringify(result.data)).not.toContain("answer_key");
    expect(JSON.stringify(result.data)).not.toContain("score");
    expect(JSON.stringify(result.data)).not.toContain("correction");
  });

  it.each(["prepared_materials", "studied_materials", "none"] as const)(
    "fetchStudyProgressSummary accepts review_basis %s",
    async (basis) => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () =>
          new Response(JSON.stringify({ ...summaryPayload(), review_basis: basis }), {
            status: 200,
            headers: { "content-type": "application/json" }
          })
        )
      );

      const result = await fetchStudyProgressSummary();

      expect(result.ok).toBe(true);
      if (!result.ok) {
        throw new Error("expected success");
      }
      expect(result.data.review_basis).toBe(basis);
    }
  );

  it("preserves backend-provided studied material counts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...summaryPayload(),
            studied_materials_count: 3,
            review_basis: "studied_materials"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchStudyProgressSummary();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.studied_materials_count).toBe(3);
    expect(result.data.review_basis).toBe("studied_materials");
  });

  it.each([
    [401, "auth_required", "Entre para acompanhar seu progresso."],
    [403, "auth_required", "Entre para acompanhar seu progresso."],
    [502, "backend_offline", "Não foi possível carregar seu resumo de progresso agora."],
    [503, "missing_base_url", "O resumo de progresso não está configurado neste ambiente."]
  ])("fetchStudyProgressSummary maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchStudyProgressSummary();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("fetchStudyProgressSummary maps missing config, mock mode, network, and invalid response safely", async () => {
    vi.mocked(getApiConfig).mockReturnValue({ baseUrl: "", forceMock: false });
    const missingConfig = await fetchStudyProgressSummary();
    expect(missingConfig.ok).toBe(false);
    if (!missingConfig.ok) {
      expect(missingConfig.error.code).toBe("missing_base_url");
    }

    vi.mocked(getApiConfig).mockReturnValue({ baseUrl: "http://127.0.0.1:8000", forceMock: true });
    const mockMode = await fetchStudyProgressSummary();
    expect(mockMode.ok).toBe(false);
    if (!mockMode.ok) {
      expect(mockMode.error.code).toBe("mock_mode");
    }

    vi.mocked(getApiConfig).mockReturnValue({ baseUrl: "http://127.0.0.1:8000", forceMock: false });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );
    const network = await fetchStudyProgressSummary();
    expect(network.ok).toBe(false);
    if (!network.ok) {
      expect(network.error.code).toBe("backend_offline");
    }

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ progress_status: "ready", source: "user_scope" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );
    const invalidShape = await fetchStudyProgressSummary();
    expect(invalidShape.ok).toBe(false);
    if (!invalidShape.ok) {
      expect(invalidShape.error.code).toBe("invalid_response");
    }
  });

  it("does not return automatic progress wording or unsafe fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...summaryPayload(),
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            correction: "CORRECTION-SHOULD-NOT-LEAK",
            score: 10,
            message: "progresso atualizado concluído"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchStudyProgressSummary();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    const dumped = JSON.stringify(result.data).toLowerCase();
    expect(dumped).not.toContain("answer_key");
    expect(dumped).not.toContain("gabarito");
    expect(dumped).not.toContain("correction");
    expect(dumped).not.toContain("score");
    expect(dumped).not.toContain("progresso atualizado");
    expect(dumped).not.toContain("concluído");
  });
});
