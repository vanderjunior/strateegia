import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { fetchStudyBlocks } from "@/lib/api/study";

function readyBlocksPayload() {
  return {
    blocks_status: "ready",
    scope_status: "connected_to_edital",
    blocks_count: 1,
    estimated_minutes: 5,
    items: [
      {
        block_id: "block-1",
        title: "Atos administrativos",
        topic_id: "topic-1",
        topic_label: "Direito Administrativo",
        subtopic_id: "subtopic-1",
        subtopic_label: "Atos administrativos",
        material_id: "doc-1",
        material_title: "Aula preparada",
        sections_count: 1,
        summary_status: "ready",
        estimated_minutes: 5,
        status: "ready",
        actions: [{ label: "Estudar bloco", href: "/study/blocks/block-1" }]
      }
    ],
    source: "user_scope"
  };
}

describe("study blocks API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("maps ready bounded blocks data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify(readyBlocksPayload()), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const result = await fetchStudyBlocks();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.blocks_status).toBe("ready");
    expect(result.data.scope_status).toBe("connected_to_edital");
    expect(result.data.items[0].title).toBe("Atos administrativos");
    expect(JSON.stringify(result.data)).not.toContain("storage_path");
    expect(JSON.stringify(result.data)).not.toContain("gabarito");
    expect(JSON.stringify(result.data)).not.toContain("token");
  });

  it("maps partial material-only blocks data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            ...readyBlocksPayload(),
            blocks_status: "partial",
            scope_status: "material_only",
            items: [
              {
                ...readyBlocksPayload().items[0],
                topic_id: null,
                topic_label: null,
                subtopic_id: null,
                subtopic_label: null
              }
            ]
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchStudyBlocks();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.blocks_status).toBe("partial");
    expect(result.data.scope_status).toBe("material_only");
    expect(result.data.items[0].topic_id).toBeNull();
  });

  it("maps not-ready blocks response to a not_ready result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            blocks_status: "not_ready",
            scope_status: "not_ready",
            blocks_count: 0,
            estimated_minutes: 0,
            items: [],
            message: "Envie e prepare um material de estudo para montar seus blocos.",
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchStudyBlocks();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected not-ready failure");
    }
    expect(result.error.code).toBe("not_ready");
    expect(result.error.message).toBe("Envie e prepare um material de estudo para montar seus blocos.");
  });

  it.each([
    [401, "auth_required", "Entre para ver seus blocos de estudo."],
    [403, "auth_required", "Entre para ver seus blocos de estudo."],
    [502, "backend_offline", "Não foi possível carregar seus blocos agora."],
    [503, "missing_base_url", "Os blocos de estudo não estão configurados neste ambiente."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchStudyBlocks();

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

    const result = await fetchStudyBlocks();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("missing_base_url");
    expect(result.source).toBe("unsupported");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("does not read real blocks in mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchStudyBlocks();

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
    const invalidJson = await fetchStudyBlocks();
    expect(invalidJson.ok).toBe(false);
    if (!invalidJson.ok) {
      expect(invalidJson.error.code).toBe("invalid_response");
    }

    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ blocks_status: "ready", source: "user_scope" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );
    const invalidShape = await fetchStudyBlocks();
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

    const result = await fetchStudyBlocks();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("backend_offline");
    expect(result.error.message).toBe("Não foi possível carregar seus blocos agora.");
  });
});
