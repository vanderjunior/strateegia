import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { fetchPipelineSummary } from "@/lib/api/pipeline";

describe("pipeline summary API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("does not attempt protected read in mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchPipelineSummary("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("mock_mode");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it.each([
    [401, "unauthorized", "Sessão necessária."],
    [403, "unauthorized", "Sessão necessária."],
    [404, "not_found", "Este conteúdo não está disponível nesta sessão."],
    [502, "backend_offline", "Não foi possível carregar os dados agora."],
    [503, "missing_base_url", "O resumo real do pipeline não está configurado neste ambiente."]
  ])("maps pipeline summary HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchPipelineSummary("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("returns the bounded pipeline summary payload on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            document_id: "doc-1",
            status: "ready_for_review",
            steps: [
              {
                key: "uploaded",
                label: "Enviado",
                state: "done",
                warnings_count: 0
              }
            ],
            steps_count: 1,
            has_ocr_warning: false,
            ready_for_review: true,
            section_count: 4,
            chunk_count: 12,
            warnings_count: 0,
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchPipelineSummary("doc-1");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.document_id).toBe("doc-1");
    expect(result.data.ready_for_review).toBe(true);
    expect(JSON.stringify(result.data)).not.toContain("token");
    expect(JSON.stringify(result.data)).not.toContain("cookie");
  });
});
