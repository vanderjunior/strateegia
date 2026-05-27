import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

vi.mock("@/lib/api/editais", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/editais")>("@/lib/api/editais");

  return {
    ...actual,
    fetchUserEditaisList: vi.fn()
  };
});

import {
  buildMockEditalDetail,
  buildMockEditaisWorkspaceViewModel,
  loadEditaisWorkspaceViewModel
} from "@/lib/adapters/editais";
import { getApiConfig } from "@/lib/api/config";
import { fetchUserEditaisList } from "@/lib/api/editais";

describe("editais adapter", () => {
  beforeEach(() => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
    vi.mocked(fetchUserEditaisList).mockReset();
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

  it("shows backend offline and keeps safe fallback when the backend is unreachable", async () => {
    vi.mocked(fetchUserEditaisList).mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: {
        code: "backend_offline",
        message: "Não foi possível conectar ao backend."
      }
    });

    const viewModel = await loadEditaisWorkspaceViewModel();

    expect(viewModel.connection.title).toBe("Backend offline");
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
});
