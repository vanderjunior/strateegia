import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

vi.mock("@/lib/api/editais", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/editais")>("@/lib/api/editais");

  return {
    ...actual,
    fetchEditalSummary: vi.fn(),
    fetchUserEditaisList: vi.fn()
  };
});

import {
  buildMockEditalDetail,
  buildMockEditaisWorkspaceViewModel,
  loadEditalDetail,
  loadEditaisWorkspaceViewModel
} from "@/lib/adapters/editais";
import { getApiConfig } from "@/lib/api/config";
import { fetchEditalSummary, fetchUserEditaisList } from "@/lib/api/editais";

describe("editais adapter", () => {
  beforeEach(() => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
    vi.mocked(fetchUserEditaisList).mockReset();
    vi.mocked(fetchEditalSummary).mockReset();
  });

  it("returns a mock-first edital overview with cautious product language", () => {
    const viewModel = buildMockEditaisWorkspaceViewModel();
    const edital = viewModel.items.find((item) => item.id === "edital-pscpp-referencia");

    expect(edital).toBeDefined();
    expect(edital?.title).toContain("PSCPP/Praticagem");
    expect(edital?.topicsCount).toBeGreaterThanOrEqual(0);
    expect(edital?.bibliographyItemsCount).toBeGreaterThanOrEqual(0);
    expect(edital?.gapsCount).toBeGreaterThanOrEqual(0);
    expect(edital?.statusLabel).toBe("Análise candidata");
    expect(edital?.reviewState).toBe("Precisa de conferência");
  });

  it("returns detail with candidates, coverage labels, and non-final wording", () => {
    const detail = buildMockEditalDetail("edital-pscpp-referencia");
    expect(detail).not.toBeNull();
    const serialized = JSON.stringify(detail);

    expect(detail?.topicCandidates.length).toBeGreaterThan(0);
    expect(detail?.bibliographyCandidates.length).toBeGreaterThan(0);
    expect(detail?.gapItems.length).toBeGreaterThan(0);
    expect(detail?.coverageItems.map((item) => item.coverageLabel)).toEqual(
      expect.arrayContaining(["Cobertura boa", "Cobertura parcial", "Gap encontrado", "Precisa de material"])
    );
    expect(detail?.notes).toEqual(
      expect.arrayContaining([
        expect.stringContaining("Alinhamento preliminar"),
        expect.stringContaining("revisão")
      ])
    );

    expect(serialized).toContain("verdade final");
    expect(serialized).not.toContain(["raw", "document", "body"].join(" "));
    expect(serialized).not.toContain(["gaba", "rito"].join(""));
  });

  it("returns null for an unknown edital detail id", () => {
    expect(buildMockEditalDetail("edital-desconhecido")).toBeNull();
  });

  it("uses real authenticated edital metadata when available", async () => {
    vi.mocked(fetchUserEditaisList).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        total_editais: 1,
        total_topics: 12,
        total_bibliography_items: 8,
        total_gaps: 3,
        items: [
          {
            edital_id: "edital-user-1",
            title: "Edital analisado da sessão",
            status: "Análise candidata",
            review_state: "Precisa de conferência",
            topics_count: 12,
            bibliography_count: 8,
            gaps_count: 3,
            coverage_status: "Cobertura parcial",
            latest_document_id: "doc-1",
            raw_text: "não deve aparecer",
            extracted_text: "não deve aparecer",
            storage_path: "uploads/user/doc-1.md"
          }
        ]
      } as never
    });

    const viewModel = await loadEditaisWorkspaceViewModel();
    const payload = JSON.stringify(viewModel);

    expect(viewModel.connection.title).toBe("Dados reais da sessão");
    expect(viewModel.items).toHaveLength(1);
    expect(viewModel.items[0]).toMatchObject({
      id: "edital-user-1",
      title: "Edital analisado da sessão",
      statusLabel: "Análise candidata",
      reviewState: "Precisa de conferência",
      topicsCount: 12,
      bibliographyItemsCount: 8,
      gapsCount: 3,
      source: "backend"
    });
    expect(payload).not.toContain("raw_text");
    expect(payload).not.toContain("extracted_text");
    expect(payload).not.toContain("storage_path");
  });

  it("shows requires session and keeps demo fallback when unauthenticated", async () => {
    vi.mocked(fetchUserEditaisList).mockResolvedValue({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "unauthorized",
        message: "Sessão necessária."
      }
    });

    const viewModel = await loadEditaisWorkspaceViewModel();

    expect(viewModel.connection.title).toBe("Requer sessão");
    expect(viewModel.items.length).toBeGreaterThan(0);
    expect(viewModel.items.some((item) => item.source === "mock")).toBe(true);
  });

  it("shows unavailable data and keeps safe fallback when the backend is unreachable", async () => {
    vi.mocked(fetchUserEditaisList).mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: {
        code: "backend_offline",
        message: "Não foi possível carregar os dados agora."
      }
    });

    const viewModel = await loadEditaisWorkspaceViewModel();

    expect(viewModel.connection.title).toBe("Dados indisponíveis");
    expect(viewModel.items.length).toBeGreaterThan(0);
    expect(viewModel.items.some((item) => item.source === "mock")).toBe(true);
  });

  it("does not attempt protected read in forced mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });

    const viewModel = await loadEditaisWorkspaceViewModel();

    expect(viewModel.connection.title).toContain("demonstração");
    expect(fetchUserEditaisList).not.toHaveBeenCalled();
  });

  it("uses real bounded edital summary for authenticated detail", async () => {
    vi.mocked(fetchEditalSummary).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
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
        source: "user_scope",
        raw_edital_text: "não deve aparecer",
        evidence: "não deve aparecer",
        storage_path: "/Users/private/edital.md"
      } as never
    });

    const viewModel = await loadEditalDetail("edital-user-1");
    const payload = JSON.stringify(viewModel);

    expect(viewModel.connection.title).toBe("Dados reais da sessão");
    expect(viewModel.connection.endpoint).toBe("/api/editais/edital-user-1/summary");
    expect(viewModel.detail).toMatchObject({
      id: "edital-user-1",
      title: "Edital analisado da sessão",
      statusLabel: "Análise candidata",
      reviewState: "Precisa de conferência",
      topicsCount: 12,
      bibliographyItemsCount: 8,
      gapsCount: 3,
      source: "backend"
    });
    expect(payload).not.toContain("raw_edital_text");
    expect(payload).not.toContain("evidence");
    expect(payload).not.toContain("storage_path");
    expect(payload).not.toContain("/Users/");
  });

  it("keeps safe fallback when edital summary requires session", async () => {
    vi.mocked(fetchEditalSummary).mockResolvedValue({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "unauthorized",
        message: "Sessão necessária."
      }
    });

    const viewModel = await loadEditalDetail("edital-pscpp-referencia");

    expect(viewModel.connection.title).toBe("Requer sessão");
    expect(viewModel.detail?.source).toBe("mock");
  });

  it("returns friendly not-found state when edital summary is outside the session", async () => {
    vi.mocked(fetchEditalSummary).mockResolvedValue({
      ok: false,
      status: 404,
      source: "backend",
      error: {
        code: "not_found",
        message: "Este conteúdo não está disponível nesta sessão."
      }
    });

    const viewModel = await loadEditalDetail("edital-fora-da-sessao");

    expect(viewModel.connection.title).toBe("Item não encontrado");
    expect(viewModel.detail).toBeNull();
  });
});
