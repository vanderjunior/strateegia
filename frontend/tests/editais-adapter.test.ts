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
            analysis_status: "not_ready",
            status: "not_ready",
            review_state: "needs_review",
            topics_count: 12,
            bibliography_count: 8,
            gaps_count: 3,
            coverage_status: "unknown",
            alignment_status: "not_available",
            warnings_count: 2,
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

    expect(viewModel.connection.title).toBe("Editais");
    expect(viewModel.items).toHaveLength(1);
    expect(viewModel.items[0]).toMatchObject({
      id: "edital-user-1",
      detailHref: "/editais/edital-user-1",
      title: "Edital recebido",
      analysisStatus: "not_ready",
      statusLabel: "Edital recebido",
      reviewState: "Análise ainda não concluída",
      topicsCount: 12,
      bibliographyItemsCount: 8,
      gapsCount: 3,
      source: "backend"
    });
    expect(payload).not.toContain("raw_text");
    expect(payload).not.toContain("extracted_text");
    expect(payload).not.toContain("storage_path");
    expect(payload).not.toContain("Análise candidata");
    expect(payload).not.toContain("Edital analisado da sessão");
  });

  it("distinguishes received editais from concluded analyses in summary metrics", async () => {
    vi.mocked(fetchUserEditaisList).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        total_editais: 6,
        total_topics: 99,
        total_bibliography_items: 99,
        total_gaps: 4,
        items: [
          {
            edital_id: "edital:analyzed-1",
            title: "Edital analisado da sessão",
            analysis_status: "analyzed",
            status: "analyzed",
            review_state: "ready_for_review",
            topics_count: 3,
            bibliography_count: 2,
            gaps_count: 1,
            coverage_status: "unknown",
            alignment_status: "not_available",
            warnings_count: 0,
            latest_document_id: "analyzed-1"
          },
          ...Array.from({ length: 5 }, (_, index) => ({
            edital_id: `edital:not-ready-${index}`,
            title: "Edital analisado da sessão",
            analysis_status: "not_ready" as const,
            status: "not_ready",
            review_state: "needs_review",
            topics_count: 0,
            bibliography_count: 0,
            gaps_count: 0,
            coverage_status: "unknown",
            alignment_status: "not_available",
            warnings_count: 1,
            latest_document_id: `not-ready-${index}`
          }))
        ]
      }
    });

    const viewModel = await loadEditaisWorkspaceViewModel();
    const summaryById = Object.fromEntries(viewModel.summary.map((item) => [item.id, item]));

    expect(summaryById["editais-enviados"]).toMatchObject({
      label: "Editais enviados",
      value: "6"
    });
    expect(summaryById["analises-concluidas"]).toMatchObject({
      label: "Análises concluídas",
      value: "1"
    });
    expect(summaryById["analises-pendentes"]).toMatchObject({
      label: "Aguardando análise ou conferência",
      value: "5"
    });
    expect(summaryById["editais-bibliografia"]).toMatchObject({
      value: "2"
    });
    expect(viewModel.items[0].detailHref).toBe("/editais/edital%3Aanalyzed-1");
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
        analysis_status: "needs_review",
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

    const viewModel = await loadEditalDetail("edital%3Auser-1");
    const payload = JSON.stringify(viewModel);

    expect(viewModel.connection.title).toBe("Informações da sua conta");
    expect(fetchEditalSummary).toHaveBeenCalledWith("edital:user-1");
    expect(viewModel.connection.endpoint).toBe("/api/editais/edital:user-1/summary");
    expect(viewModel.detail).toMatchObject({
      id: "edital:user-1",
      title: "Edital analisado da sessão",
      statusLabel: "Edital analisado, mas precisa de conferência",
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

  it("uses received-only copy for not-ready edital summary", async () => {
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
        analysis_status: "not_ready",
        topics_count: 0,
        bibliography_count: 0,
        gaps_count: 0,
        review_state: "needs_review",
        coverage_status: "unknown",
        alignment_status: "not_available",
        warnings_count: 2,
        summary: {
          has_topics: false,
          has_bibliography: false,
          has_gaps: false,
          needs_review: true
        },
        source: "user_scope"
      }
    });

    const viewModel = await loadEditalDetail("edital-user-1");
    const payload = JSON.stringify(viewModel);

    expect(viewModel.detail).toMatchObject({
      title: "Edital recebido",
      analysisStatus: "not_ready",
      statusLabel: "Edital recebido",
      reviewState: "Análise ainda não concluída",
      topicCandidates: [],
      bibliographyCandidates: [],
      coverageItems: [],
      gapItems: []
    });
    expect(payload).toContain("Este edital foi recebido, mas ainda não há tópicos ou bibliografia prontos");
    expect(payload).toContain("Confira se o arquivo tem texto extraível");
    expect(payload).not.toContain("Edital analisado da sessão");
    expect(payload).not.toContain("Análise candidata");
    expect(payload).not.toContain("Alinhamento preliminar");
    expect(payload).not.toContain("tópicos candidatos identificados");
    expect(payload).not.toContain("Cobertura do edital");
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
