import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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
  const readiness = actual.buildDefaultRealUserStudyReadiness({
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
    buildDefaultRealUserStudyReadiness: vi.fn(() => readiness),
    loadRealUserStudyReadiness: vi.fn(async () => readiness)
  };
});

import { EditaisReadOnlyClient } from "@/components/workspace/EditaisReadOnlyClient";
import { EditalDetailReadOnlyClient } from "@/components/workspace/EditalDetailReadOnlyClient";
import { MaterialUploadEntryClient } from "@/components/workspace/MaterialUploadEntryClient";
import { MaterialsReadOnlyClient } from "@/components/workspace/MaterialsReadOnlyClient";

describe("materials, editais, and upload read-only invariants", () => {
  it("keeps materials workspace on product-friendly read-only CTAs", async () => {
    render(<MaterialsReadOnlyClient />);

    expect((await screen.findAllByText("Ver detalhes")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Enviar material").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Disponível para consulta").length).toBeGreaterThan(0);
    expect(screen.getByText("Materiais por classificação")).toBeInTheDocument();
    expect(screen.getAllByText("Editais").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Materiais de estudo").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tipo não informado").length).toBeGreaterThan(0);
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
    expect(screen.getAllByText("Requer sessão").length).toBeGreaterThan(0);

    expect(screen.queryByText("Ingerir edital")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
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
