import { getApiConfig } from "@/lib/api/config";
import { fetchDocumentById } from "@/lib/api/documents";
import { fetchMaterialChunks, fetchMaterialPipelineState, fetchMaterialSections } from "@/lib/api/pipeline";
import { fetchDashboardOverview } from "@/lib/api/runtime";
import type {
  ApiSource,
  BackendConnectionInfo,
  BackendDocumentPipelineState,
  BackendDocumentSection,
  MaterialDetail,
  MaterialsWorkspaceViewModel,
  MaterialListItem,
  WorkspaceSummaryMetric
} from "@/lib/api/types";
import { materialDetailsById, materialsWorkspaceItems } from "@/lib/mock/mentorium-demo-data";
import { getUserFacingCapability } from "@/lib/product/product-language";

function cloneItems<T>(items: readonly T[]): T[] {
  return items.map((item) => ({ ...item }));
}

function cloneDetail(detail: MaterialDetail): MaterialDetail {
  return {
    ...detail,
    warnings: [...detail.warnings],
    sectionPreviews: detail.sectionPreviews.map((section) => ({ ...section }))
  };
}

function baseConnection(overrides: Partial<BackendConnectionInfo> = {}): BackendConnectionInfo {
  return {
    state: "mock",
    source: "mock",
    title: "Usando dados de demonstração",
    detail: "A listagem permanece em modo de demonstração até existir leitura segura da listagem real.",
    ...overrides
  };
}

function workspaceSummary(
  processed: number,
  ocrRequired: number,
  readyForReview: number,
  relatedGaps: number
): WorkspaceSummaryMetric[] {
  return [
    {
      id: "materials-processed",
      label: "Materiais processados",
      value: String(processed),
      detail: "Materiais com leitura concluída e etapa de revisão liberada."
    },
    {
      id: "materials-ocr",
      label: "OCR necessário",
      value: String(ocrRequired),
      detail: "Arquivos digitalizados que ainda dependem de validação."
    },
    {
      id: "materials-review",
      label: "Prontos para revisão",
      value: String(readyForReview),
      detail: "Itens já organizados para leitura e revisão orientada."
    },
    {
      id: "materials-gaps",
      label: "Gaps relacionados",
      value: String(relatedGaps),
      detail: "Pontos de cobertura ainda associados a esses materiais."
    }
  ];
}

function mockSummary(items: MaterialListItem[]): WorkspaceSummaryMetric[] {
  const processed = items.filter((item) => item.processingStatus === "Processado").length;
  const ocrRequired = items.filter((item) => item.processingStatus === "OCR necessário").length;
  const readyForReview = items.filter((item) => item.reviewState === "Pronto para revisão").length;
  const relatedGaps = items.reduce((total, item) => total + item.relatedGaps, 0);
  return workspaceSummary(processed, ocrRequired, readyForReview, relatedGaps);
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

function normalizeProcessingStatus(state: BackendDocumentPipelineState): string {
  if (state.extraction_status.includes("ocr")) {
    return "OCR necessário";
  }
  if (state.metadata_status === "ready" || state.metadata_status === "metadata_ready") {
    return "Processado";
  }
  if (state.current_stage.includes("pending")) {
    return "Processando";
  }
  return "Precisa de revisão";
}

function normalizeExtractionStatus(state: BackendDocumentPipelineState): string {
  if (state.extraction_status.includes("ocr")) {
    return "OCR em validação";
  }
  if (state.extraction_status === "extracted" || state.extraction_status === "sectioned") {
    return "Texto extraído";
  }
  return "Leitura em validação";
}

function normalizeReviewState(state: BackendDocumentPipelineState): string {
  if (state.extraction_status.includes("ocr")) {
    return "OCR em validação";
  }
  if (state.metadata_status === "ready" || state.metadata_status === "metadata_ready") {
    return "Pronto para revisão";
  }
  return "Precisa de revisão";
}

function normalizeWarnings(state: BackendDocumentPipelineState): string[] {
  if (state.extraction_status.includes("ocr")) {
    return ["Este arquivo pode precisar de OCR antes da revisão.", "OCR em validação."];
  }
  return ["Texto extraído sujeito a revisão."];
}

function mapSectionPreview(sections: BackendDocumentSection[]) {
  return sections.slice(0, 8).map((section) => ({
    id: section.section_id,
    title: section.title,
    level: section.level,
    chunkRangeLabel: `Trechos ${section.start_chunk_index + 1} a ${section.end_chunk_index + 1}`
  }));
}

export function buildMockMaterialsWorkspaceViewModel(): MaterialsWorkspaceViewModel {
  const items = cloneItems(materialsWorkspaceItems);
  return {
    connection: baseConnection(),
    summary: mockSummary(items),
    items
  };
}

export async function loadMaterialsWorkspaceViewModel(): Promise<MaterialsWorkspaceViewModel> {
  const config = getApiConfig();
  const fallback = buildMockMaterialsWorkspaceViewModel();

  if (config.forceMock) {
    return {
      ...fallback,
      connection: baseConnection({
        title: "Mock forçado por configuração",
        detail: "NEXT_PUBLIC_USE_MOCK_API=true manteve esta área em modo local."
      })
    };
  }

  if (!config.baseUrl) {
    return {
      ...fallback,
      connection: baseConnection({
        detail: "Defina NEXT_PUBLIC_API_BASE_URL para habilitar leituras read-only autenticadas quando disponíveis."
      })
    };
  }

  const overviewResult = await fetchDashboardOverview();
  if (!overviewResult.ok) {
    if (overviewResult.status === 401) {
      return {
        ...fallback,
        connection: {
          state: "auth_required",
          source: "backend",
          title: "Sessão necessária",
          detail:
            "O backend está disponível, mas a visão de materiais continua protegida até existir uma sessão válida no navegador.",
          endpoint: "/api/dashboard/overview"
        }
      };
    }
    return {
      ...fallback,
      connection: connectionFromFailure(overviewResult.source, overviewResult.error.message, "/api/dashboard/overview")
    };
  }

  return {
    ...fallback,
    connection: {
      state: "connected",
      source: "backend",
      title: "Backend conectado com fallback auditado",
      detail:
        "Os contadores foram lidos do backend em modo somente leitura. A lista detalhada ainda usa dados de demonstração seguros.",
      endpoint: "/api/dashboard/overview"
    },
    summary: workspaceSummary(
      overviewResult.data.materials.processed_count,
      overviewResult.data.materials.ocr_required_count,
      overviewResult.data.document_pipeline.sectioned_count,
      overviewResult.data.alignment.gaps_detected
    )
  };
}

export function buildMockMaterialDetail(materialId: string): MaterialDetail {
  const detail = materialDetailsById[materialId] ?? {
    id: materialId,
    title: "Material em validação",
    typeLabel: getUserFacingCapability("document_pipeline", "student")?.label ?? "Material",
    processingStatus: "Precisa de revisão",
    extractionStatus: "Leitura em validação",
    sectionsCount: null,
    chunksCount: null,
    reviewState: "Precisa de revisão",
    source: "mock" as const,
    relatedGaps: 0,
    warnings: ["Nenhum detalhe adicional disponível ainda."],
    sectionPreviews: [],
    sourceNote: "Este material ainda não possui leitura detalhada disponível nesta área."
  };

  return cloneDetail(detail);
}

export async function loadMaterialDetail(materialId: string): Promise<{
  connection: BackendConnectionInfo;
  detail: MaterialDetail;
}> {
  const config = getApiConfig();
  const fallback = buildMockMaterialDetail(materialId);

  if (config.forceMock) {
    return {
      connection: baseConnection({
        title: "Mock forçado por configuração",
        detail: "NEXT_PUBLIC_USE_MOCK_API=true manteve este material em modo local."
      }),
      detail: fallback
    };
  }

  if (!config.baseUrl) {
    return {
      connection: baseConnection({
        detail: "Defina NEXT_PUBLIC_API_BASE_URL para tentar ler este material em modo somente leitura."
      }),
      detail: fallback
    };
  }

  const [pipelineResult, sectionsResult, chunksResult, documentResult] = await Promise.all([
    fetchMaterialPipelineState(materialId),
    fetchMaterialSections(materialId),
    fetchMaterialChunks(materialId),
    fetchDocumentById(materialId)
  ]);

  if (!pipelineResult.ok) {
    if (pipelineResult.status === 401) {
      return {
        connection: {
          state: "auth_required",
          source: "backend",
          title: "Sessão necessária",
          detail: "Os detalhes reais do material exigem uma sessão válida para leitura em modo somente leitura.",
          endpoint: `/api/materials/${materialId}/pipeline`
        },
        detail: fallback
      };
    }

    return {
      connection: connectionFromFailure(
        pipelineResult.source,
        pipelineResult.error.message,
        `/api/materials/${materialId}/pipeline`
      ),
      detail: fallback
    };
  }

  const pipeline = pipelineResult.data;
  const title = documentResult.ok ? documentResult.data.title : fallback.title;
  const detail: MaterialDetail = {
    id: materialId,
    title,
    typeLabel: pipeline.extraction_status.includes("ocr") ? "PDF digitalizado" : "PDF textual",
    processingStatus: normalizeProcessingStatus(pipeline),
    extractionStatus: normalizeExtractionStatus(pipeline),
    sectionsCount: sectionsResult.ok ? sectionsResult.data.length : pipeline.section_count,
    chunksCount: chunksResult.ok ? chunksResult.data.length : pipeline.chunk_count,
    reviewState: normalizeReviewState(pipeline),
    source: "backend",
    relatedGaps: fallback.relatedGaps,
    warnings: normalizeWarnings(pipeline),
    sectionPreviews: sectionsResult.ok ? mapSectionPreview(sectionsResult.data) : fallback.sectionPreviews,
    sourceNote: "Dados lidos do backend em modo somente leitura e apresentados sem conteúdo bruto."
  };

  return {
    connection: {
      state: "connected",
      source: "backend",
      title: "Detalhes carregados do backend",
      detail: "Este material foi lido em modo somente leitura, preservando a revisão controlada.",
      endpoint: `/api/materials/${materialId}/pipeline`
    },
    detail
  };
}
