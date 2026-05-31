import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { fetchEditalSummary, fetchUserEditaisList } from "@/lib/api/editais";
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
    [502, "backend_offline", "Não foi possível carregar os dados agora."],
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
                analysis_status: "not_ready",
                status: "not_ready",
                review_state: "needs_review",
                topics_count: 12,
                bibliography_count: 8,
                gaps_count: 3,
                coverage_status: "unknown",
                alignment_status: "not_available",
                warnings_count: 2
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
    expect(result.data.items[0].analysis_status).toBe("not_ready");
    expect(result.data.items[0].review_state).toBe("needs_review");
    expect(JSON.stringify(result.data)).not.toContain("Análise candidata");
    expect(JSON.stringify(result.data)).not.toContain("token");
    expect(JSON.stringify(result.data)).not.toContain("cookie");
  });

  it.each([
    [401, "unauthorized", "Sessão necessária."],
    [403, "unauthorized", "Sessão necessária."],
    [404, "not_found", "Este conteúdo não está disponível nesta sessão."],
    [502, "backend_offline", "Não foi possível carregar os dados agora."],
    [503, "missing_base_url", "O resumo real do edital não está configurado neste ambiente."]
  ])("maps edital summary HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchEditalSummary("edital-user-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("returns the bounded edital summary payload on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            edital_id: "edital-user-1",
            document_id: "doc-1",
            title: "Edital analisado da sessão",
            created_at: "2026-05-27T00:00:00Z",
            updated_at: "2026-05-27T00:05:00Z",
            topics_count: 12,
            bibliography_count: 8,
            gaps_count: 3,
            review_state: "needs_review",
            coverage_status: "partial",
            alignment_status: "needs_review",
            warnings_count: 2,
            summary: {
              has_topics: true,
              has_bibliography: true,
              has_gaps: true,
              needs_review: true
            },
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchEditalSummary("edital-user-1");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.edital_id).toBe("edital-user-1");
    expect(result.data.summary.needs_review).toBe(true);
    expect(JSON.stringify(result.data)).not.toContain("token");
    expect(JSON.stringify(result.data)).not.toContain("cookie");
  });
});
