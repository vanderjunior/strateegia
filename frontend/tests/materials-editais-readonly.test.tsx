import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const realUserStateMock = vi.hoisted(() => ({
  readiness: undefined as unknown
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
import { MaterialUploadEntryClient } from "@/components/workspace/MaterialUploadEntryClient";
import { MaterialsReadOnlyClient } from "@/components/workspace/MaterialsReadOnlyClient";
import { loadMaterialsWorkspaceViewModel } from "@/lib/adapters/materials";
import { loadEditaisWorkspaceViewModel } from "@/lib/adapters/editais";

describe("materials, editais, and upload read-only invariants", () => {
  beforeEach(() => {
    realUserStateMock.readiness = undefined;
  });

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
});
