import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/adapters/materials", () => ({
  buildMockMaterialDetail: vi.fn(() => null),
  loadMaterialDetail: vi.fn(async () => ({
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Consulta local exibida até existir leitura segura do backend para este material."
    },
    detail: null
  }))
}));

vi.mock("@/lib/adapters/editais", () => ({
  buildMockEditalDetail: vi.fn(() => null),
  loadEditalDetail: vi.fn(async () => ({
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Consulta local exibida até existir leitura segura do backend para este edital."
    },
    detail: null
  }))
}));

vi.mock("@/lib/adapters/pipeline", () => ({
  buildMockPipelineDetail: vi.fn(() => null),
  loadPipelineDetail: vi.fn(async () => ({
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Consulta local exibida até existir leitura segura do backend para este material."
    },
    detail: null
  }))
}));

vi.mock("@/lib/adapters/study-sessions", () => ({
  buildMockStudySessionDetail: vi.fn(() => null),
  loadStudySessionDetail: vi.fn(async () => null),
  loadStudySessionWorkspaceViewModel: vi.fn(async () => ({
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Sessão exibida por consulta local auditada enquanto a leitura do perfil PSCPP no backend não é necessária para este detalhe."
    },
    summary: [],
    nextSuggestedSessionId: "sessao-desconhecida",
    sessions: [],
    highlightedGaps: [],
    starterMaterials: []
  }))
}));

import { EditalDetailReadOnlyClient } from "@/components/workspace/EditalDetailReadOnlyClient";
import { MaterialDetailReadOnlyClient } from "@/components/workspace/MaterialDetailReadOnlyClient";
import { PipelineDetailReadOnlyClient } from "@/components/workspace/PipelineDetailReadOnlyClient";
import { StudySessionDetailClient } from "@/components/workspace/StudySessionDetailClient";

describe("detail and fallback states", () => {
  it("shows product-friendly fallbacks for unknown detail routes", async () => {
    render(
      <div>
        <MaterialDetailReadOnlyClient materialId="material-desconhecido" />
        <EditalDetailReadOnlyClient editalId="edital-desconhecido" />
        <PipelineDetailReadOnlyClient documentId="pipeline-desconhecido" />
        <StudySessionDetailClient sessionId="sessao-desconhecida" />
      </div>
    );

    expect((await screen.findAllByText("Item não encontrado")).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Este conteúdo não está disponível nesta sessão\./).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Voltar para materiais").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Voltar para editais").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Voltar para estudo").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ver mapa PSCPP").length).toBeGreaterThan(0);

    expect(screen.queryByText("undefined")).not.toBeInTheDocument();
    expect(screen.queryByText("null")).not.toBeInTheDocument();
    expect(screen.queryByText("NaN")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
  });
});
