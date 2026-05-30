import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { analyzeMaterialAsEdital } from "@/lib/api/editais";

describe("controlled edital analysis API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("returns bounded analyzed response on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            edital_id: "edital:doc-1",
            document_id: "doc-1",
            analysis_status: "analyzed",
            review_state: "ready_for_review",
            topics_count: 3,
            bibliography_count: 2,
            gaps_count: 0,
            warnings_count: 0,
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await analyzeMaterialAsEdital("doc-1");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.analysis_status).toBe("analyzed");
    expect(JSON.stringify(result.data)).not.toContain("token");
    expect(JSON.stringify(result.data)).not.toContain("storage_path");
  });

  it("returns bounded needs_review response on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            edital_id: "edital:doc-1",
            document_id: "doc-1",
            analysis_status: "needs_review",
            review_state: "needs_review",
            topics_count: 3,
            bibliography_count: 2,
            gaps_count: 1,
            warnings_count: 2,
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await analyzeMaterialAsEdital("doc-1");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.analysis_status).toBe("needs_review");
  });

  it.each([
    [401, "unauthorized", "Entre para analisar edital."],
    [403, "unauthorized", "Entre para analisar edital."],
    [404, "not_found", "Material não encontrado."],
    [422, "invalid_material_type", "Este material não está classificado como edital."],
    [502, "backend_offline", "Não foi possível concluir a análise agora."],
    [503, "missing_base_url", "A análise do edital não está configurada neste ambiente."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await analyzeMaterialAsEdital("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("maps not_ready lifecycle response to a product-safe not-ready result", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            edital_id: "edital:doc-1",
            document_id: "doc-1",
            analysis_status: "not_ready",
            review_state: "needs_review",
            topics_count: 0,
            bibliography_count: 0,
            gaps_count: 0,
            warnings_count: 1,
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await analyzeMaterialAsEdital("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("not_ready");
    expect(result.error.message).toBe("O edital ainda não está pronto para análise.");
  });

  it("does not attempt analysis in mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await analyzeMaterialAsEdital("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("mock_mode");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("maps network failures to backend offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const result = await analyzeMaterialAsEdital("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("backend_offline");
    expect(result.source).toBe("offline");
  });
});
