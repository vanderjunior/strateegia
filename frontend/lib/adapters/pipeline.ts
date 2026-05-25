import { getApiConfig } from "@/lib/api/config";
import { fetchDocumentById } from "@/lib/api/documents";
import { fetchMaterialChunks, fetchMaterialPipelineState, fetchMaterialSections } from "@/lib/api/pipeline";
import type {
  ApiSource,
  BackendConnectionInfo,
  BackendDocumentPipelineState,
  PipelineDetailViewModel,
  PipelineStep
} from "@/lib/api/types";
import { pipelineDetailsById } from "@/lib/mock/mentorium-demo-data";

function cloneSteps(steps: readonly PipelineStep[]): PipelineStep[] {
  return steps.map((step) => ({ ...step }));
}

function cloneViewModel(viewModel: PipelineDetailViewModel): PipelineDetailViewModel {
  return {
    ...viewModel,
    steps: cloneSteps(viewModel.steps),
    notes: [...viewModel.notes]
  };
}

function baseConnection(overrides: Partial<BackendConnectionInfo> = {}): BackendConnectionInfo {
  return {
    state: "mock",
    source: "mock",
    title: "Usando dados de demonstração",
    detail: "A linha do tempo permanece em modo de demonstração até existir leitura segura do backend para este material.",
    ...overrides
  };
}

function connectionFromFailure(source: ApiSource, message: string, endpoint: string): BackendConnectionInfo {
  if (source === "unsupported") {
    return baseConnection({
      state: "unsupported",
      source,
      title: "Painel em modo de validação",
      detail: message,
      endpoint
    });
  }
  if (source === "offline") {
    return baseConnection({
      state: "offline",
      source,
      title: "Backend indisponível",
      detail: message,
      endpoint
    });
  }
  return baseConnection({
    state: "mock",
    source,
    title: "Fallback local ativo",
    detail: message,
    endpoint
  });
}

function buildSteps(state: BackendDocumentPipelineState): PipelineStep[] {
  const extracted = state.extraction_status === "extracted" || state.extraction_status === "sectioned";
  const ocrRequired = state.extraction_status.includes("ocr");
  const sectioned = state.section_count > 0 || state.sectioning_status === "completed";
  const ready = state.metadata_status === "ready" || state.metadata_status === "metadata_ready";

  return [
    {
      id: "uploaded",
      label: "Enviado",
      statusLabel: "Concluído",
      tone: "complete",
      detail: "Material já registrado para leitura controlada."
    },
    {
      id: "extracted",
      label: "Texto extraído",
      statusLabel: ocrRequired ? "OCR necessário" : extracted ? "Concluído" : "Em validação",
      tone: ocrRequired ? "warning" : extracted ? "complete" : "current",
      detail: ocrRequired
        ? "A leitura textual ainda depende de OCR ou validação."
        : "A leitura textual foi preparada sem expor conteúdo bruto."
    },
    {
      id: "segmented",
      label: "Segmentado",
      statusLabel: sectioned ? "Concluído" : "Pendente",
      tone: sectioned ? "complete" : "pending",
      detail: sectioned ? "Trechos e seções já podem ser revisados." : "A segmentação ainda não está pronta."
    },
    {
      id: "review",
      label: "Pronto para revisão",
      statusLabel: ready ? "Concluído" : ocrRequired ? "Em validação" : "Pendente",
      tone: ready ? "current" : ocrRequired ? "warning" : "pending",
      detail: ready
        ? "O material já está em etapa de revisão."
        : "O material segue em preparação controlada para revisão."
    }
  ];
}

export function buildMockPipelineDetail(documentId: string): PipelineDetailViewModel {
  const detail = pipelineDetailsById[documentId] ?? {
    connection: baseConnection(),
    documentId,
    title: "Pipeline em validação",
    source: "mock" as const,
    extractionStatus: "Leitura em validação",
    reviewState: "Precisa de revisão",
    sectionsCount: null,
    chunksCount: null,
    notes: ["Nenhum detalhe adicional disponível ainda."],
    steps: [
      { id: "uploaded", label: "Enviado", statusLabel: "Concluído", tone: "complete", detail: "Material registrado." },
      { id: "extracted", label: "Texto extraído", statusLabel: "Pendente", tone: "pending", detail: "Leitura textual ainda não confirmada." },
      { id: "segmented", label: "Segmentado", statusLabel: "Pendente", tone: "pending", detail: "Segmentação ainda não disponível." },
      { id: "review", label: "Pronto para revisão", statusLabel: "Pendente", tone: "pending", detail: "Etapa de revisão ainda não liberada." }
    ]
  };

  return cloneViewModel(detail);
}

export async function loadPipelineDetail(documentId: string): Promise<PipelineDetailViewModel> {
  const config = getApiConfig();
  const fallback = buildMockPipelineDetail(documentId);

  if (config.forceMock) {
    return {
      ...fallback,
      connection: baseConnection({
        title: "Mock forçado por configuração",
        detail: "NEXT_PUBLIC_USE_MOCK_API=true manteve esta linha do tempo em modo local."
      })
    };
  }

  if (!config.baseUrl) {
    return {
      ...fallback,
      connection: baseConnection({
        detail: "Defina NEXT_PUBLIC_API_BASE_URL para tentar ler esta linha do tempo em modo somente leitura."
      })
    };
  }

  const [pipelineResult, sectionsResult, chunksResult, documentResult] = await Promise.all([
    fetchMaterialPipelineState(documentId),
    fetchMaterialSections(documentId),
    fetchMaterialChunks(documentId),
    fetchDocumentById(documentId)
  ]);

  if (!pipelineResult.ok) {
    if (pipelineResult.status === 401) {
      return {
        ...fallback,
        connection: {
          state: "auth_required",
          source: "backend",
          title: "Sessão necessária",
          detail: "A linha do tempo real do material exige uma sessão válida para leitura em modo somente leitura.",
          endpoint: `/api/materials/${documentId}/pipeline`
        }
      };
    }
    return {
      ...fallback,
      connection: connectionFromFailure(
        pipelineResult.source,
        pipelineResult.error.message,
        `/api/materials/${documentId}/pipeline`
      )
    };
  }

  const pipeline = pipelineResult.data;

  return {
    connection: {
      state: "connected",
      source: "backend",
      title: "Linha do tempo carregada do backend",
      detail: "O pipeline foi lido em modo somente leitura e resumido em linguagem de produto.",
      endpoint: `/api/materials/${documentId}/pipeline`
    },
    documentId,
    title: documentResult.ok ? documentResult.data.title : fallback.title,
    source: "backend",
    extractionStatus: pipeline.extraction_status.includes("ocr") ? "OCR em validação" : "Texto extraído",
    reviewState:
      pipeline.metadata_status === "ready" || pipeline.metadata_status === "metadata_ready"
        ? "Pronto para revisão"
        : pipeline.extraction_status.includes("ocr")
          ? "OCR necessário"
          : "Precisa de revisão",
    sectionsCount: sectionsResult.ok ? sectionsResult.data.length : pipeline.section_count,
    chunksCount: chunksResult.ok ? chunksResult.data.length : pipeline.chunk_count,
    notes: pipeline.extraction_status.includes("ocr")
      ? ["Este arquivo pode precisar de OCR antes da revisão."]
      : ["Texto extraído sujeito a revisão."],
    steps: buildSteps(pipeline)
  };
}
