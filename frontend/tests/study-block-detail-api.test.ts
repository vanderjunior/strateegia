import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { fetchStudyBlockDetail } from "@/lib/api/study";

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

describe("study block detail API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("maps ready bounded detail data", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify(readyDetailPayload()), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchStudyBlockDetail("study-block:topic-1:doc-1:0");

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/study/blocks/study-block%3Atopic-1%3Adoc-1%3A0",
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
    expect(result.data.detail_status).toBe("ready");
    expect(result.data.sections[0].title).toBe("Atos administrativos");
    expect(JSON.stringify(result.data)).not.toContain("storage_path");
    expect(JSON.stringify(result.data)).not.toContain("gabarito");
    expect(JSON.stringify(result.data)).not.toContain("token");
  });

  it("maps needs-review bounded detail data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...readyDetailPayload(),
            detail_status: "needs_review",
            summary_status: "needs_review",
            topic_id: null,
            topic_label: null,
            subtopic_id: null,
            subtopic_label: null,
            sections: [{ ...readyDetailPayload().sections[0], status: "needs_review" }]
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchStudyBlockDetail("block-1");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.detail_status).toBe("needs_review");
    expect(result.data.summary_status).toBe("needs_review");
    expect(result.data.topic_id).toBeNull();
  });

  it("maps not-ready detail data to a not_ready result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...readyDetailPayload(),
            detail_status: "not_ready",
            summary_status: "not_ready",
            sections: []
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchStudyBlockDetail("block-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected not-ready failure");
    }
    expect(result.error.code).toBe("not_ready");
    expect(result.error.message).toBe("Este bloco ainda não está pronto para estudo.");
  });

  it.each([
    [401, "auth_required", "Entre para ver este bloco de estudo."],
    [403, "auth_required", "Entre para ver este bloco de estudo."],
    [404, "not_found", "Bloco de estudo não encontrado."],
    [502, "backend_offline", "Não foi possível carregar este bloco agora."],
    [503, "missing_base_url", "Este bloco de estudo não está configurado neste ambiente."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchStudyBlockDetail("block-1");

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

    const result = await fetchStudyBlockDetail("block-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("missing_base_url");
    expect(result.source).toBe("unsupported");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("does not read real detail in mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchStudyBlockDetail("block-1");

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
    const invalidJson = await fetchStudyBlockDetail("block-1");
    expect(invalidJson.ok).toBe(false);
    if (!invalidJson.ok) {
      expect(invalidJson.error.code).toBe("invalid_response");
    }

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail_status: "ready", source: "user_scope" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );
    const invalidShape = await fetchStudyBlockDetail("block-1");
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

    const result = await fetchStudyBlockDetail("block-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("backend_offline");
    expect(result.error.message).toBe("Não foi possível carregar este bloco agora.");
  });
});
