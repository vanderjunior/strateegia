import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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

vi.mock("@/lib/adapters/pipeline", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/pipeline")>(
    "@/lib/adapters/pipeline"
  );

  return {
    ...actual,
    loadPipelineDetail: vi.fn(async (documentId: string) => ({
      connection: {
        state: "mock",
        source: "mock",
        title: "Dados de demonstração",
        detail: "Consulta local exibida até existir leitura segura do backend para este material."
      },
      detail: actual.buildMockPipelineDetail(documentId)
    }))
  };
});

import { EditaisReadOnlyClient } from "@/components/workspace/EditaisReadOnlyClient";
import { EditalDetailReadOnlyClient } from "@/components/workspace/EditalDetailReadOnlyClient";
import { MaterialDetailReadOnlyClient } from "@/components/workspace/MaterialDetailReadOnlyClient";
import { MaterialUploadEntryClient } from "@/components/workspace/MaterialUploadEntryClient";
import { MaterialsReadOnlyClient } from "@/components/workspace/MaterialsReadOnlyClient";
import { PipelineDetailReadOnlyClient } from "@/components/workspace/PipelineDetailReadOnlyClient";

describe("materials, editais, and pipeline copy", () => {
  it("keeps product-facing language across materials, editais, upload, and pipeline surfaces", async () => {
    render(
      <div>
        <MaterialsReadOnlyClient />
        <MaterialDetailReadOnlyClient materialId="material-arte-naval" />
        <MaterialUploadEntryClient />
        <EditaisReadOnlyClient />
        <EditalDetailReadOnlyClient editalId="edital-pscpp-referencia" />
        <PipelineDetailReadOnlyClient documentId="material-roteiro-porto" />
      </div>
    );

    expect((await screen.findAllByText("Dados de demonstração")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Enviar material").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Material processado").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Análise candidata").length).toBeGreaterThan(0);
    expect(screen.getByText("Linha do processamento")).toBeInTheDocument();
    expect(screen.getAllByText("OCR em validação").length).toBeGreaterThan(0);

    expect(screen.queryByText(/artifact/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/runtime chain/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/raw OCR/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/base64/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Processar")).not.toBeInTheDocument();
    expect(screen.queryByText("Reprocessar")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
    expect(screen.queryByText("Agendar")).not.toBeInTheDocument();
  });
});
