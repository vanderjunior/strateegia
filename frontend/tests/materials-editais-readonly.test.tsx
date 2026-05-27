import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/adapters/session", () => ({
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
  }))
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
        detail: "Consulta local exibida até existir leitura segura do backend para este material."
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
        detail: "Consulta local exibida até existir leitura segura do backend para este edital."
      },
      detail: actual.buildMockEditalDetail(editalId)
    }))
  };
});

import { EditaisReadOnlyClient } from "@/components/workspace/EditaisReadOnlyClient";
import { EditalDetailReadOnlyClient } from "@/components/workspace/EditalDetailReadOnlyClient";
import { MaterialUploadEntryClient } from "@/components/workspace/MaterialUploadEntryClient";
import { MaterialsReadOnlyClient } from "@/components/workspace/MaterialsReadOnlyClient";

describe("materials, editais, and upload read-only invariants", () => {
  it("keeps materials workspace on product-friendly read-only CTAs", async () => {
    render(<MaterialsReadOnlyClient />);

    expect((await screen.findAllByText("Ver material")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Enviar material").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Texto extraído").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pronto para revisão").length).toBeGreaterThan(0);
    expect(screen.getAllByText("OCR necessário").length).toBeGreaterThan(0);
    expect(screen.getByText("Requer sessão")).toBeInTheDocument();

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

    expect((await screen.findAllByText("Ver edital")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Análise candidata").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Precisa de conferência").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Gaps encontrados").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Cobertura parcial").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Requer sessão").length).toBeGreaterThan(0);

    expect(screen.queryByText("Ingerir edital")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
  });

  it("keeps upload entry free of process and generation controls", () => {
    render(<MaterialUploadEntryClient />);

    expect(screen.getByRole("button", { name: "Enviar para validação" })).toBeInTheDocument();
    expect(screen.queryByText("Processar")).not.toBeInTheDocument();
    expect(screen.queryByText("Reprocessar")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
    expect(screen.queryByText("Concluir sessão")).not.toBeInTheDocument();
    expect(screen.queryByText("Agendar")).not.toBeInTheDocument();
  });
});
