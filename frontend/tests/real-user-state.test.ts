import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

vi.mock("@/lib/api/documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/documents")>("@/lib/api/documents");

  return {
    ...actual,
    fetchUserMaterialsList: vi.fn()
  };
});

vi.mock("@/lib/api/editais", () => ({
  fetchUserEditaisList: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { fetchUserMaterialsList } from "@/lib/api/documents";
import { fetchUserEditaisList } from "@/lib/api/editais";
import { loadRealUserStudyReadiness } from "@/lib/adapters/real-user-state";

function mockMaterials(items: unknown[]) {
  vi.mocked(fetchUserMaterialsList).mockResolvedValue({
    ok: true,
    status: 200,
    source: "backend",
    data: {
      total_materials: items.length,
      processed_count: 0,
      pending_count: items.length,
      ocr_required_count: 0,
      items
    } as never
  });
}

function mockEditais(items: unknown[]) {
  vi.mocked(fetchUserEditaisList).mockResolvedValue({
    ok: true,
    status: 200,
    source: "backend",
    data: {
      total_editais: items.length,
      total_topics: 0,
      total_bibliography_items: 0,
      total_gaps: 0,
      items
    } as never
  });
}

describe("real user edital analysis state", () => {
  beforeEach(() => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
    vi.mocked(fetchUserMaterialsList).mockReset();
    vi.mocked(fetchUserEditaisList).mockReset();
  });

  it("detects no uploaded edital from real materials metadata", async () => {
    mockMaterials([]);
    mockEditais([]);

    const readiness = await loadRealUserStudyReadiness();

    expect(readiness.editalAnalysisState).toBe("no_edital_uploaded");
    expect(readiness.editalAnalysisLabel).toBe("Nenhum edital enviado");
    expect(readiness.canShowConcreteStudyPlan).toBe(false);
    expect(readiness.shouldShowEditalUploadCTA).toBe(true);
  });

  it("detects uploaded-but-not-analyzed edital from material_type only", async () => {
    mockMaterials([
      {
        document_id: "doc-edital",
        display_filename: "edital.pdf",
        content_type: "application/pdf",
        material_type: "edital",
        extraction_status: "pending",
        chunk_count: 0,
        section_count: 0
      }
    ]);
    mockEditais([]);

    const readiness = await loadRealUserStudyReadiness();

    expect(readiness.editalAnalysisState).toBe("edital_uploaded_not_analyzed");
    expect(readiness.editalAnalysisDescription).toBe("Edital recebido. A análise ainda não foi executada nesta versão.");
    expect(readiness.canShowConcreteStudyPlan).toBe(false);
    expect(readiness.shouldShowStudyMaterialCTA).toBe(true);
  });

  it("allows concrete study only when bounded edital data is analyzed and ready", async () => {
    mockMaterials([]);
    mockEditais([
      {
        edital_id: "edital-1",
        title: "Edital analisado",
        analysis_status: "analyzed",
        status: "ready",
        review_state: "ready_for_review",
        topics_count: 8,
        bibliography_count: 4,
        gaps_count: 0,
        coverage_status: "good"
      }
    ]);

    const readiness = await loadRealUserStudyReadiness();

    expect(readiness.editalAnalysisState).toBe("edital_analyzed");
    expect(readiness.editalAnalysisLabel).toBe("Edital analisado");
    expect(readiness.hasAnalyzedEdital).toBe(true);
    expect(readiness.canShowConcreteStudyPlan).toBe(true);
  });

  it("keeps needs-review analysis from becoming concrete study guidance", async () => {
    mockMaterials([]);
    mockEditais([
      {
        edital_id: "edital-1",
        title: "Edital preliminar",
        analysis_status: "needs_review",
        status: "Análise candidata",
        review_state: "needs_review",
        topics_count: 8,
        bibliography_count: 4,
        gaps_count: 2,
        coverage_status: "partial",
        raw_text: "não deve aparecer",
        storage_path: "/Users/private/edital.md"
      }
    ]);

    const readiness = await loadRealUserStudyReadiness();
    const payload = JSON.stringify(readiness);

    expect(readiness.editalAnalysisState).toBe("analysis_needs_review");
    expect(readiness.editalAnalysisLabel).toBe("Precisa de conferência");
    expect(readiness.hasAnalyzedEdital).toBe(true);
    expect(readiness.canShowConcreteStudyPlan).toBe(false);
    expect(payload).not.toContain("raw_text");
    expect(payload).not.toContain("storage_path");
    expect(payload).not.toContain("/Users/");
  });

  it("keeps explicit failed lifecycle unavailable and locked", async () => {
    mockMaterials([{ document_id: "doc-edital", display_filename: "edital.pdf", material_type: "edital" }]);
    mockEditais([
      {
        edital_id: "edital-1",
        title: "Edital indisponível",
        analysis_status: "failed",
        status: "unknown",
        review_state: "unknown",
        topics_count: 0,
        bibliography_count: 0,
        gaps_count: 0,
        coverage_status: "unknown"
      }
    ]);

    const readiness = await loadRealUserStudyReadiness();

    expect(readiness.editalAnalysisState).toBe("analysis_unavailable");
    expect(readiness.editalAnalysisLabel).toBe("Análise indisponível");
    expect(readiness.canShowConcreteStudyPlan).toBe(false);
  });

  it("keeps not-ready edital lifecycle uploaded-only and locked", async () => {
    mockMaterials([{ document_id: "doc-edital", display_filename: "edital.pdf", material_type: "edital" }]);
    mockEditais([
      {
        edital_id: "edital-1",
        title: "Edital recebido",
        analysis_status: "not_ready",
        status: "not_ready",
        review_state: "needs_review",
        topics_count: 0,
        bibliography_count: 0,
        gaps_count: 0,
        coverage_status: "unknown",
        alignment_status: "not_available",
        warnings_count: 2
      }
    ]);

    const readiness = await loadRealUserStudyReadiness();

    expect(readiness.editalAnalysisState).toBe("edital_uploaded_not_analyzed");
    expect(readiness.editalAnalysisLabel).toBe("Edital enviado");
    expect(readiness.hasAnalyzedEdital).toBe(false);
    expect(readiness.canShowConcreteStudyPlan).toBe(false);
  });

  it("marks analysis unavailable when protected reads cannot determine state", async () => {
    mockMaterials([]);
    vi.mocked(fetchUserEditaisList).mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: {
        code: "backend_offline",
        message: "Dados reais não carregados agora."
      }
    });

    const readiness = await loadRealUserStudyReadiness();

    expect(readiness.editalAnalysisState).toBe("analysis_unavailable");
    expect(readiness.editalAnalysisLabel).toBe("Análise indisponível");
    expect(readiness.canShowConcreteStudyPlan).toBe(false);
  });
});
