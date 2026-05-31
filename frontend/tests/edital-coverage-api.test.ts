import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { fetchEditalCoverage } from "@/lib/api/editais";
import { getApiConfig } from "@/lib/api/config";

describe("edital coverage API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("returns bounded coverage data on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            edital_id: "edital-user-1",
            analysis_status: "analyzed",
            coverage_status: "partial",
            topics_count: 1,
            subtopics_count: 3,
            covered_subtopics_count: 1,
            partial_subtopics_count: 1,
            uncovered_subtopics_count: 1,
            out_of_scope_materials_count: 0,
            materials_considered_count: 1,
            items: [
              {
                topic_id: "topic-1",
                label: "Lingua Portuguesa",
                subtopics_count: 3,
                covered_count: 1,
                partial_count: 1,
                uncovered_count: 1,
                status: "partial"
              }
            ],
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchEditalCoverage("edital-user-1");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.edital_id).toBe("edital-user-1");
    expect(result.data.coverage_status).toBe("partial");
    expect(result.data.items[0].status).toBe("partial");
    expect(JSON.stringify(result.data)).not.toContain("token");
    expect(JSON.stringify(result.data)).not.toContain("storage_path");
    expect(JSON.stringify(result.data)).not.toContain("gabarito");
  });

  it("maps not-ready coverage to a product-safe not-ready result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            edital_id: "edital-user-1",
            analysis_status: "not_ready",
            coverage_status: "not_ready",
            topics_count: 0,
            subtopics_count: 0,
            covered_subtopics_count: 0,
            partial_subtopics_count: 0,
            uncovered_subtopics_count: 0,
            out_of_scope_materials_count: 0,
            materials_considered_count: 0,
            items: [],
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchEditalCoverage("edital-user-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("not_ready");
    expect(result.error.message).toBe("A cobertura ainda não está pronta para este edital.");
  });

  it.each([
    [401, "auth_required", "Entre para ver a cobertura do edital."],
    [403, "auth_required", "Entre para ver a cobertura do edital."],
    [404, "not_found", "Edital não encontrado."],
    [502, "backend_offline", "Não foi possível consultar a cobertura agora."],
    [503, "missing_base_url", "A cobertura do edital não está configurada neste ambiente."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchEditalCoverage("edital-user-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("maps missing local config to unsupported", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "",
      forceMock: false
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchEditalCoverage("edital-user-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("missing_base_url");
    expect(result.source).toBe("unsupported");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("does not attempt coverage read in mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchEditalCoverage("edital-user-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("mock_mode");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("maps invalid JSON to invalid_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{", { status: 200, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchEditalCoverage("edital-user-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("invalid_response");
  });

  it("maps invalid bounded shape to invalid_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ edital_id: "edital-user-1", coverage_status: "partial" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const result = await fetchEditalCoverage("edital-user-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("invalid_response");
  });

  it("maps network errors to backend_offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const result = await fetchEditalCoverage("edital-user-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("backend_offline");
    expect(result.error.message).toBe("Não foi possível consultar a cobertura agora.");
  });
});
