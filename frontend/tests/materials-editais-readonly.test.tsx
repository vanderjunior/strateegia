import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const realUserStateMock = vi.hoisted(() => ({
  readiness: undefined as unknown
}));

const editalAnalysisMock = vi.hoisted(() => ({
  analyzeMaterialAsEdital: vi.fn()
}));

vi.mock("@/lib/adapters/session", () => ({
  SESSION_STATE_CHANGED_EVENT: "mentorium:session-state-changed",
  buildDefaultSessionState: vi.fn(() => ({
    status: "unauthenticated",
    label: "Sessão necessária",
    description: "Entre para usar dados reais. Enquanto isso, o painel usa dados de demonstração.",
    source: "backend"
  })),
  loadSessionState: vi.fn(async () => ({
    status: "unauthenticated",
    label: "Sessão necessária",
    description: "Entre para usar dados reais. Enquanto isso, o painel usa dados de demonstração.",
    source: "backend"
  })),
  notifySessionStateChanged: vi.fn()
}));

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn(() => ({
    baseUrl: "http://127.0.0.1:8000",
    forceMock: false
  }))
}));

vi.mock("@/lib/api/editais", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/editais")>(
    "@/lib/api/editais"
  );

  return {
    ...actual,
    analyzeMaterialAsEdital: editalAnalysisMock.analyzeMaterialAsEdital
  };
});

vi.mock("@/lib/adapters/materials", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/materials")>(
    "@/lib/adapters/materials"
  );

  return {
    ...actual,
    loadMaterialsWorkspaceViewModel: vi.fn(async () => actual.buildMockMaterialsWorkspaceViewModel()),
    loadMaterialDetail: vi.fn(async (materialId: string) => ({
      connection: {
        state: "mock",
        source: "mock",
        title: "Dados de demonstração",
        detail: "Demonstração exibida até existir leitura segura para este material."
      },
      detail: actual.buildMockMaterialDetail(materialId)
    }))
  };
});

vi.mock("@/lib/adapters/editais", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/editais")>(
    "@/lib/adapters/editais"
  );

  return {
    ...actual,
    loadEditaisWorkspaceViewModel: vi.fn(async () => actual.buildMockEditaisWorkspaceViewModel()),
    loadEditalDetail: vi.fn(async (editalId: string) => ({
      connection: {
        state: "mock",
        source: "mock",
        title: "Dados de demonstração",
        detail: "Demonstração exibida até existir leitura segura para este edital."
      },
      detail: actual.buildMockEditalDetail(editalId)
    }))
  };
});

vi.mock("@/lib/adapters/real-user-state", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/real-user-state")>(
    "@/lib/adapters/real-user-state"
  );
  const defaultReadiness = actual.buildDefaultRealUserStudyReadiness({
    connection: {
      state: "auth_required",
      source: "backend",
      title: "Entre para carregar seus dados",
      detail: "A orientação real depende de uma sessão ativa."
    },
    isAuthenticated: false,
    hasRealEditalMaterial: false,
    hasAnalyzedEdital: false,
    editalAnalysisState: "no_edital_uploaded",
    canShowConcreteStudyPlan: false
  });

  return {
    ...actual,
    buildDefaultRealUserStudyReadiness: vi.fn((overrides) => actual.buildDefaultRealUserStudyReadiness(overrides)),
    loadRealUserStudyReadiness: vi.fn(async () => realUserStateMock.readiness ?? defaultReadiness)
  };
});

import { EditaisReadOnlyClient } from "@/components/workspace/EditaisReadOnlyClient";
import { EditalDetailReadOnlyClient } from "@/components/workspace/EditalDetailReadOnlyClient";
import { MaterialDetailReadOnlyClient } from "@/components/workspace/MaterialDetailReadOnlyClient";
import { MaterialUploadEntryClient } from "@/components/workspace/MaterialUploadEntryClient";
import { MaterialsReadOnlyClient } from "@/components/workspace/MaterialsReadOnlyClient";
import { loadMaterialDetail, loadMaterialsWorkspaceViewModel } from "@/lib/adapters/materials";
import { loadEditaisWorkspaceViewModel } from "@/lib/adapters/editais";
import type { MaterialDetail } from "@/lib/api/types";

describe("materials, editais, and upload read-only invariants", () => {
  beforeEach(() => {
    realUserStateMock.readiness = undefined;
    editalAnalysisMock.analyzeMaterialAsEdital.mockReset();
  });

  function backendMaterialDetail(overrides: Partial<MaterialDetail> = {}): MaterialDetail {
    return {
      id: "doc-edital",
      title: "edital-pscpp",
      typeLabel: "TXT",
      materialType: "edital",
      materialTypeLabel: "Edital",
      processingStatus: "Material processado",
      extractionStatus: "Texto extraído",
      sectionsCount: 2,
      chunksCount: 8,
      reviewState: "Pronto para revisão",
      source: "backend",
      relatedGaps: 0,
      warnings: ["Este resumo mostra apenas metadados seguros do material."],
      sectionPreviews: [],
      sourceNote: "Resumo carregado por consulta protegida.",
      ...overrides
    };
  }

  it("keeps materials workspace on product-friendly read-only CTAs", async () => {
    render(<MaterialsReadOnlyClient />);

    expect((await screen.findAllByText("Ver detalhes")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Enviar material").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Disponível para consulta").length).toBeGreaterThan(0);
    expect(screen.getByText("Materiais por classificação")).toBeInTheDocument();
    expect(screen.queryByText("Editais 0")).not.toBeInTheDocument();
    expect(screen.queryByText("Materiais de estudo 0")).not.toBeInTheDocument();
    expect(screen.getByText("Envie um edital para orientar o caminho de estudo.")).toBeInTheDocument();
    expect(screen.getByText("Requer sessão")).toBeInTheDocument();
    expect(screen.queryByText(/0 seções/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Gaps relacionados: 0/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Consulta local/i)).not.toBeInTheDocument();

    expect(screen.queryByText("Processar")).not.toBeInTheDocument();
    expect(screen.queryByText("Reprocessar")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
    expect(screen.queryByText("Agendar")).not.toBeInTheDocument();
  });

  it("explains legacy materials when the list is mostly untyped", async () => {
    vi.mocked(loadMaterialsWorkspaceViewModel).mockResolvedValueOnce({
      connection: {
        state: "connected",
        source: "backend",
        title: "Materiais",
        detail: "Materiais disponíveis."
      },
      summary: [],
      items: [
        {
          id: "doc-1",
          title: "arquivo-antigo-1",
          typeLabel: "TXT",
          materialType: "unknown",
          materialTypeLabel: "Tipo não informado",
          processingStatus: "Recebido para validação",
          extractionStatus: "Leitura em validação",
          sectionsCount: 0,
          chunksCount: 0,
          reviewState: "Precisa de conferência",
          source: "backend",
          relatedGaps: 0
        },
        {
          id: "doc-2",
          title: "arquivo-antigo-2",
          typeLabel: "TXT",
          materialType: "unknown",
          materialTypeLabel: "Tipo não informado",
          processingStatus: "Recebido para validação",
          extractionStatus: "Leitura em validação",
          sectionsCount: 0,
          chunksCount: 0,
          reviewState: "Precisa de conferência",
          source: "backend",
          relatedGaps: 0
        }
      ],
      materialTypeGroups: [
        { type: "edital", label: "Editais", count: 0, items: [] },
        { type: "study_material", label: "Materiais de estudo", count: 0, items: [] },
        { type: "previous_exam", label: "Provas anteriores", count: 0, items: [] },
        { type: "bibliography", label: "Bibliografia / referência", count: 0, items: [] },
        { type: "note", label: "Anotações / resumos", count: 0, items: [] },
        { type: "other", label: "Outros", count: 0, items: [] },
        {
          type: "unknown",
          label: "Tipo não informado",
          count: 2,
          items: [
            {
              id: "doc-1",
              title: "arquivo-antigo-1",
              typeLabel: "TXT",
              materialType: "unknown",
              materialTypeLabel: "Tipo não informado",
              processingStatus: "Recebido para validação",
              extractionStatus: "Leitura em validação",
              sectionsCount: 0,
              chunksCount: 0,
              reviewState: "Precisa de conferência",
              source: "backend",
              relatedGaps: 0
            },
            {
              id: "doc-2",
              title: "arquivo-antigo-2",
              typeLabel: "TXT",
              materialType: "unknown",
              materialTypeLabel: "Tipo não informado",
              processingStatus: "Recebido para validação",
              extractionStatus: "Leitura em validação",
              sectionsCount: 0,
              chunksCount: 0,
              reviewState: "Precisa de conferência",
              source: "backend",
              relatedGaps: 0
            }
          ]
        }
      ],
      hasEdital: false,
      hasStudyMaterial: false,
      unclassifiedCount: 2
    });

    render(<MaterialsReadOnlyClient />);

    expect(await screen.findByText(/Alguns arquivos foram enviados antes da classificação por tipo/i)).toBeInTheDocument();
    expect(screen.getByText(/Novos envios podem ser classificados como edital/i)).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.queryByText("Editais 0")).not.toBeInTheDocument();
    expect(screen.queryByText("Materiais de estudo 0")).not.toBeInTheDocument();
  });

  it("keeps editais workspace and detail on cautious candidate language", async () => {
    render(
      <div>
        <EditaisReadOnlyClient />
        <EditalDetailReadOnlyClient editalId="edital-pscpp-referencia" />
      </div>
    );

    expect(await screen.findByText("Nenhum edital analisado ainda.")).toBeInTheDocument();
    expect(screen.getByText(/Entre para ver seus editais analisados/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Enviar edital" })).toHaveAttribute("href", "/materials/upload");
    expect(screen.getAllByText("Análise candidata").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Precisa de conferência").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Gaps encontrados").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Cobertura parcial").length).toBeGreaterThan(0);
    expect(screen.getByText(/Entre para ver seus editais analisados/i)).toBeInTheDocument();

    expect(screen.queryByText("Ingerir edital")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText(/leitura protegida/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Dados reais da sessão/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/demonstração continua disponível/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/sessão reconhecida/i)).not.toBeInTheDocument();
  });

  it("shows a product empty state for editais without protected-read wording", async () => {
    realUserStateMock.readiness = {
      connection: {
        state: "connected",
        source: "backend",
        title: "Dados reais disponíveis",
        detail: "Materiais disponíveis."
      },
      isAuthenticated: true,
      hasRealMaterials: false,
      hasRealEditalMaterial: false,
      hasRealStudyMaterial: false,
      hasAnalyzedEdital: false,
      editalAnalysisState: "no_edital_uploaded",
      editalAnalysisLabel: "Nenhum edital enviado",
      editalAnalysisDescription: "Envie um edital para orientar seu caminho de estudo.",
      canShowConcreteStudyPlan: false,
      shouldShowEditalUploadCTA: true,
      shouldShowStudyMaterialCTA: false,
      materialsCount: 0,
      editalMaterialsCount: 0,
      studyMaterialsCount: 0,
      materialTypeCounts: {
        edital: 0,
        study_material: 0,
        previous_exam: 0,
        bibliography: 0,
        note: 0,
        other: 0,
        unknown: 0
      }
    };

    vi.mocked(loadEditaisWorkspaceViewModel).mockResolvedValueOnce({
      connection: {
        state: "connected",
        source: "backend",
        title: "Editais",
        detail: "Editais disponíveis."
      },
      summary: [],
      items: []
    });

    render(<EditaisReadOnlyClient />);

    expect(await screen.findByText("Nenhum edital analisado ainda.")).toBeInTheDocument();
    expect(screen.getByText("Envie um arquivo classificado como edital para iniciar esse fluxo.")).toBeInTheDocument();
    expect(screen.queryByText(/leitura protegida/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Dados reais da sessão/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/demonstração/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/sessão reconhecida/i)).not.toBeInTheDocument();
  });

  it("shows not-ready edital lifecycle without analyzed or candidate wording", async () => {
    realUserStateMock.readiness = {
      connection: {
        state: "connected",
        source: "backend",
        title: "Dados reais disponíveis",
        detail: "Materiais disponíveis."
      },
      isAuthenticated: true,
      hasRealMaterials: true,
      hasRealEditalMaterial: true,
      hasRealStudyMaterial: false,
      hasAnalyzedEdital: false,
      editalAnalysisState: "edital_uploaded_not_analyzed",
      editalAnalysisLabel: "Edital enviado",
      editalAnalysisDescription: "Edital recebido. A análise ainda não foi executada nesta versão.",
      canShowConcreteStudyPlan: false,
      shouldShowEditalUploadCTA: false,
      shouldShowStudyMaterialCTA: true,
      materialsCount: 1,
      editalMaterialsCount: 1,
      studyMaterialsCount: 0,
      materialTypeCounts: {
        edital: 1,
        study_material: 0,
        previous_exam: 0,
        bibliography: 0,
        note: 0,
        other: 0,
        unknown: 0
      }
    };

    vi.mocked(loadEditaisWorkspaceViewModel).mockResolvedValueOnce({
      connection: {
        state: "connected",
        source: "backend",
        title: "Editais",
        detail: "Editais disponíveis."
      },
      summary: [],
      items: [
        {
          id: "edital:doc-1",
          title: "Edital analisado da sessão",
          statusLabel: "Edital recebido",
          topicsCount: 0,
          bibliographyItemsCount: 0,
          gapsCount: 0,
          reviewState: "Análise ainda não concluída",
          source: "backend"
        }
      ]
    });

    render(<EditaisReadOnlyClient />);

    expect(await screen.findByText("Edital recebido")).toBeInTheDocument();
    expect(screen.getByText("Análise ainda não concluída")).toBeInTheDocument();
    expect(screen.queryByText("Edital analisado")).not.toBeInTheDocument();
    expect(screen.queryByText("Análise candidata")).not.toBeInTheDocument();
  });

  it("keeps upload entry gated and free of process and generation controls without a session", async () => {
    render(<MaterialUploadEntryClient />);

    expect(await screen.findByText("Entre para enviar materiais.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enviar arquivo" })).not.toBeInTheDocument();
    expect(screen.queryByText("Processar")).not.toBeInTheDocument();
    expect(screen.queryByText("Reprocessar")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
    expect(screen.queryByText("Concluir sessão")).not.toBeInTheDocument();
    expect(screen.queryByText("Agendar")).not.toBeInTheDocument();
  });

  it("does not show edital analysis action for non-edital material detail", async () => {
    vi.mocked(loadMaterialDetail).mockResolvedValueOnce({
      connection: {
        state: "connected",
        source: "backend",
        title: "Materiais",
        detail: "Material disponível."
      },
      detail: backendMaterialDetail({
        id: "doc-study",
        materialType: "study_material",
        materialTypeLabel: "Material de estudo"
      })
    });

    render(<MaterialDetailReadOnlyClient materialId="doc-study" />);

    expect(await screen.findByText("edital-pscpp")).toBeInTheDocument();
    expect(screen.queryByText("Análise do edital")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Analisar edital" })).not.toBeInTheDocument();
  });

  it("shows the minimal edital analysis action only for a real edital material", async () => {
    vi.mocked(loadMaterialDetail).mockResolvedValueOnce({
      connection: {
        state: "connected",
        source: "backend",
        title: "Materiais",
        detail: "Material disponível."
      },
      detail: backendMaterialDetail()
    });

    render(<MaterialDetailReadOnlyClient materialId="doc-edital" />);

    expect(await screen.findByText("Análise do edital")).toBeInTheDocument();
    expect(screen.getByText(/Este arquivo foi marcado como edital/i)).toBeInTheDocument();
    expect(screen.getByText("Esta etapa não gera questões, simulados nem altera seu progresso.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analisar edital" })).toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
  });

  it("runs edital analysis and shows bounded analyzed success with counts", async () => {
    vi.mocked(loadMaterialDetail).mockResolvedValueOnce({
      connection: {
        state: "connected",
        source: "backend",
        title: "Materiais",
        detail: "Material disponível."
      },
      detail: backendMaterialDetail()
    });
    editalAnalysisMock.analyzeMaterialAsEdital.mockResolvedValueOnce({
      ok: true,
      data: {
        edital_id: "edital:doc-edital",
        document_id: "doc-edital",
        analysis_status: "analyzed",
        review_state: "ready_for_review",
        topics_count: 4,
        bibliography_count: 2,
        gaps_count: 0,
        warnings_count: 0,
        source: "user_scope"
      },
      status: 200,
      source: "backend"
    });

    render(<MaterialDetailReadOnlyClient materialId="doc-edital" />);
    fireEvent.click(await screen.findByRole("button", { name: "Analisar edital" }));

    expect(screen.getByRole("button", { name: "Analisando edital..." })).toBeDisabled();
    await waitFor(() => expect(screen.getByText("Edital analisado.")).toBeInTheDocument());
    expect(screen.getByText("4 tópicos · 2 bibliografia · 0 gaps")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver editais" })).toHaveAttribute("href", "/editais");
    expect(editalAnalysisMock.analyzeMaterialAsEdital).toHaveBeenCalledWith("doc-edital");
  });

  it("shows safe edital analysis status messages", async () => {
    vi.mocked(loadMaterialDetail).mockResolvedValue({
      connection: {
        state: "connected",
        source: "backend",
        title: "Materiais",
        detail: "Material disponível."
      },
      detail: backendMaterialDetail()
    });

    const cases = [
      {
        result: {
          ok: true,
          data: {
            edital_id: "edital:doc-edital",
            document_id: "doc-edital",
            analysis_status: "needs_review",
            review_state: "needs_review",
            topics_count: 4,
            bibliography_count: 2,
            gaps_count: 1,
            warnings_count: 1,
            source: "user_scope"
          },
          status: 200,
          source: "backend"
        },
        message: "Edital analisado, mas precisa de conferência."
      },
      {
        result: {
          ok: false,
          status: 200,
          source: "backend",
          error: { code: "not_ready", message: "O edital ainda não está pronto para análise." }
        },
        message: "Este edital ainda não está pronto para análise. Confira se o arquivo tem texto extraível ou envie uma versão textual."
      },
      {
        result: {
          ok: false,
          status: 422,
          source: "backend",
          error: { code: "invalid_material_type", message: "Este material não está classificado como edital." }
        },
        message: "Este material não está classificado como edital."
      },
      {
        result: {
          ok: false,
          status: 404,
          source: "backend",
          error: { code: "not_found", message: "Material não encontrado." }
        },
        message: "Material não encontrado nesta sessão."
      },
      {
        result: {
          ok: false,
          status: 502,
          source: "offline",
          error: { code: "backend_offline", message: "Não foi possível concluir a análise agora." }
        },
        message: "Não foi possível concluir a análise agora."
      }
    ] as const;

    for (const testCase of cases) {
      editalAnalysisMock.analyzeMaterialAsEdital.mockResolvedValueOnce(testCase.result);
      const { unmount } = render(<MaterialDetailReadOnlyClient materialId="doc-edital" />);

      fireEvent.click(await screen.findByRole("button", { name: "Analisar edital" }));

      await waitFor(() => expect(screen.getByText(testCase.message)).toBeInTheDocument());
      expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
      expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
      expect(screen.queryByText("Executar simulado")).not.toBeInTheDocument();
      expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
      expect(document.body.textContent).not.toContain("storage_path");
      expect(document.body.textContent).not.toContain("gabarito");
      expect(document.body.textContent).not.toContain("token");
      unmount();
    }
  });
});
