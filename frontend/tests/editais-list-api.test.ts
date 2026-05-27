import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { fetchUserEditaisList } from "@/lib/api/editais";
import { getApiConfig } from "@/lib/api/config";

describe("editais list API wrapper", () => {
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

    const result = await fetchUserEditaisList();

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
    [502, "backend_offline", "Não foi possível conectar ao backend."],
    [503, "missing_base_url", "A listagem real de editais não está configurada neste ambiente."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchUserEditaisList();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("returns the safe editais list payload on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            total_editais: 1,
            total_topics: 12,
            total_bibliography_items: 8,
            total_gaps: 3,
            items: [
              {
                edital_id: "edital-user-1",
                latest_document_id: "doc-1",
                title: "Edital analisado da sessão",
                status: "Análise candidata",
                review_state: "Precisa de conferência",
                topics_count: 12,
                bibliography_count: 8,
                gaps_count: 3,
                coverage_status: "Cobertura parcial"
              }
            ]
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchUserEditaisList();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.items[0].edital_id).toBe("edital-user-1");
    expect(JSON.stringify(result.data)).not.toContain("token");
    expect(JSON.stringify(result.data)).not.toContain("cookie");
  });
});
