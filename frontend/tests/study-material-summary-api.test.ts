import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { fetchStudyMaterialSummary } from "@/lib/api/documents";

describe("study material summary API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("returns the bounded study material summary payload on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            document_id: "doc-1",
            summary_status: "ready",
            material_type: "study_material",
            title: "Aula",
            sections_count: 1,
            items: [
              {
                section_id: "section-1",
                title: "Atos administrativos",
                summary: "Resumo em preparação para esta seção.",
                key_points: ["Atos administrativos"],
                estimated_minutes: 8,
                status: "ready"
              }
            ],
            warnings_count: 0,
            source: "user_scope",
            extracted_text: "RAW-SHOULD-NOT-LEAK",
            storage_path: "/Users/private/aula.md",
            token: "TOKEN-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchStudyMaterialSummary("doc-1");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data).toEqual({
      document_id: "doc-1",
      summary_status: "ready",
      material_type: "study_material",
      title: "Aula",
      sections_count: 1,
      items: [
        {
          section_id: "section-1",
          title: "Atos administrativos",
          summary: "Resumo em preparação para esta seção.",
          key_points: ["Atos administrativos"],
          estimated_minutes: 8,
          status: "ready"
        }
      ],
      warnings_count: 0,
      source: "user_scope"
    });
    expect(JSON.stringify(result.data)).not.toContain("extracted_text");
    expect(JSON.stringify(result.data)).not.toContain("storage_path");
    expect(JSON.stringify(result.data)).not.toContain("TOKEN-SHOULD-NOT-LEAK");
  });

  it("maps not_ready summary payload to a product-safe not_ready result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            document_id: "doc-1",
            summary_status: "not_ready",
            material_type: "study_material",
            title: "Aula",
            sections_count: 0,
            items: [],
            warnings_count: 0,
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchStudyMaterialSummary("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("not_ready");
    expect(result.error.message).toBe("O resumo ainda não está pronto para este material.");
  });

  it.each([
    [401, "auth_required", "Entre para ver o resumo do material."],
    [403, "auth_required", "Entre para ver o resumo do material."],
    [404, "not_found", "Material não encontrado."],
    [422, "invalid_material_type", "Este arquivo não está classificado como material de estudo."],
    [502, "backend_offline", "Não foi possível consultar o resumo agora."],
    [503, "missing_base_url", "O resumo do material não está configurado neste ambiente."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchStudyMaterialSummary("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("maps missing local API configuration to unsupported without fetching", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: null,
      forceMock: false
    });

    const result = await fetchStudyMaterialSummary("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("missing_base_url");
    expect(result.error.message).toBe("O resumo do material não está configurado neste ambiente.");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("does not attempt protected read in mock mode", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });

    const result = await fetchStudyMaterialSummary("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("mock_mode");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("maps invalid response shape to invalid_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ document_id: "doc-1", summary_status: "surprise" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const result = await fetchStudyMaterialSummary("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("invalid_response");
    expect(result.error.message).toBe("Não foi possível consultar o resumo agora.");
  });

  it("maps invalid JSON to invalid_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response("{not-json", {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const result = await fetchStudyMaterialSummary("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("invalid_response");
  });

  it("maps network failures to backend_offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const result = await fetchStudyMaterialSummary("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("backend_offline");
    expect(result.error.message).toBe("Não foi possível consultar o resumo agora.");
  });
});
