import { getApiConfig } from "@/lib/api/config";
import { fetchMaterialSummary, fetchUserMaterialsList, materialTypeLabel, normalizeMaterialType } from "@/lib/api/documents";
import type {
  ApiSource,
  BackendConnectionInfo,
  BackendMaterialSummary,
  BackendProtectedMaterialsListItem,
  MaterialDetail,
  MaterialType,
  MaterialTypeGroup,
  MaterialsWorkspaceViewModel,
  MaterialListItem,
  WorkspaceSummaryMetric
} from "@/lib/api/types";
import { materialDetailsById, materialsWorkspaceItems } from "@/lib/mock/mentorium-demo-data";

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
    title: "Dados de demonstração",
    detail: "Demonstração exibida até existir leitura segura da listagem real.",
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
  const processed = items.filter((item) => item.processingStatus === "Material processado").length;
  const ocrRequired = items.filter((item) => item.processingStatus === "OCR necessário").length;
  const readyForReview = items.filter((item) => item.reviewState === "Pronto para revisão").length;
  const relatedGaps = items.reduce((total, item) => total + item.relatedGaps, 0);
  return workspaceSummary(processed, ocrRequired, readyForReview, relatedGaps);
}

const MATERIAL_TYPE_GROUPS: { type: MaterialType; label: string }[] = [
  { type: "edital", label: "Editais" },
  { type: "study_material", label: "Materiais de estudo" },
  { type: "previous_exam", label: "Provas anteriores" },
  { type: "bibliography", label: "Bibliografia / referência" },
  { type: "note", label: "Anotações / resumos" },
  { type: "other", label: "Outros" },
  { type: "unknown", label: "Tipo não informado" }
];

function buildMaterialTypeGroups(items: MaterialListItem[]): MaterialTypeGroup[] {
  return MATERIAL_TYPE_GROUPS.map((group) => {
    const groupItems = items.filter((item) => item.materialType === group.type);
    return {
      ...group,
      count: groupItems.length,
      items: groupItems
    };
  });
}

function withMaterialTypeGrouping(
  viewModel: Omit<MaterialsWorkspaceViewModel, "materialTypeGroups" | "hasEdital" | "hasStudyMaterial" | "unclassifiedCount">
): MaterialsWorkspaceViewModel {
  const materialTypeGroups = buildMaterialTypeGroups(viewModel.items);
  return {
    ...viewModel,
    materialTypeGroups,
    hasEdital: materialTypeGroups.some((group) => group.type === "edital" && group.count > 0),
    hasStudyMaterial: materialTypeGroups.some((group) => group.type === "study_material" && group.count > 0),
    unclassifiedCount: materialTypeGroups.find((group) => group.type === "unknown")?.count ?? 0
  };
}

function trimFileExtension(filename: string): string {
  return filename.replace(/\.[a-z0-9]+$/i, "");
}

function fileTypeLabel(item: BackendProtectedMaterialsListItem): string {
  if (item.extraction_status.includes("ocr")) {
    return "PDF digitalizado";
  }
  if (item.content_type === "md" || item.content_type === "text/markdown" || item.display_filename.toLowerCase().endsWith(".md")) {
    return "Markdown";
  }
  if (item.content_type === "txt" || item.content_type === "text/plain" || item.display_filename.toLowerCase().endsWith(".txt")) {
    return "TXT";
  }
  if (item.content_type === "pdf" || item.content_type.includes("pdf") || item.display_filename.toLowerCase().endsWith(".pdf")) {
    return "PDF textual";
  }
  return "Material de apoio";
}

function mapProtectedMaterialItem(item: BackendProtectedMaterialsListItem): MaterialListItem {
  const normalizedStatus = `${item.status ?? item.processing_status ?? ""} ${item.current_stage ?? item.latest_pipeline_status ?? ""}`.toLowerCase();
  const extraction = item.extraction_status.toLowerCase();
  const metadataStatus = (item.metadata_status ?? item.review_state ?? "").toLowerCase();

  const processingStatus = extraction.includes("ocr")
    ? "OCR necessário"
    : metadataStatus === "ready" ||
        metadataStatus === "metadata_ready" ||
        metadataStatus === "ready_for_review" ||
        normalizedStatus.includes("metadata_ready") ||
        normalizedStatus.includes("ready_for_review")
      ? "Material processado"
      : normalizedStatus.includes("uploaded") || normalizedStatus.includes("pending")
        ? "Recebido para validação"
        : "Precisa de conferência";

  const extractionStatus = extraction.includes("ocr")
    ? "OCR em validação"
    : extraction === "extracted" || extraction === "sectioned" || extraction === "chunked"
      ? "Texto extraído"
      : "Leitura em validação";

  const reviewState = extraction.includes("ocr")
    ? "OCR em validação"
    : metadataStatus === "ready" || metadataStatus === "metadata_ready" || metadataStatus === "ready_for_review"
      ? "Pronto para revisão"
      : "Precisa de conferência";

  return {
    id: item.document_id,
    title: trimFileExtension(item.display_filename),
    typeLabel: fileTypeLabel(item),
    materialType: normalizeMaterialType(item.material_type),
    materialTypeLabel: materialTypeLabel(item.material_type),
    processingStatus,
    extractionStatus,
    sectionsCount: item.section_count,
    chunksCount: item.chunk_count,
    reviewState,
    source: "backend",
    relatedGaps: 0
  };
}

function connectionFromFailure(source: ApiSource, message: string, endpoint: string): BackendConnectionInfo {
  if (source === "unsupported") {
    return baseConnection({
      state: "unsupported",
      source,
      title: "Demonstração",
      detail: "Esta área segue em validação neste ambiente. Os dados de demonstração continuam disponíveis.",
      endpoint
    });
  }
  if (source === "offline") {
    return baseConnection({
      state: "offline",
      source,
      title: "Dados indisponíveis",
      detail: "Não foi possível carregar dados reais agora. Os dados de demonstração continuam disponíveis.",
      endpoint
    });
  }
  return baseConnection({
    state: "mock",
    source,
    title: "Dados de demonstração",
    detail: "Demonstração exibida até existir uma leitura segura para esta área.",
    endpoint
  });
}

function normalizeMaterialProcessingStatus(summary: BackendMaterialSummary): string {
  const processing = summary.processing_status.toLowerCase();
  const extraction = summary.extraction_status.toLowerCase();
  const pipelineStatus = (summary.latest_pipeline_status ?? summary.pipeline.status ?? "").toLowerCase();

  if (extraction.includes("ocr") || processing.includes("ocr") || summary.pipeline.has_ocr_warning) {
    return "OCR necessário";
  }
  if (
    summary.review_state === "ready_for_review" ||
    summary.pipeline.ready_for_review ||
    pipelineStatus.includes("metadata_ready") ||
    pipelineStatus.includes("ready")
  ) {
    return "Material processado";
  }
  if (processing.includes("uploaded") || processing.includes("pending")) {
    return "Recebido para validação";
  }
  return "Precisa de conferência";
}

function normalizeMaterialExtractionStatus(summary: BackendMaterialSummary): string {
  const extraction = summary.extraction_status.toLowerCase();

  if (extraction.includes("ocr") || summary.pipeline.has_ocr_warning) {
    return "OCR em validação";
  }
  if (["textual_pdf", "extracted", "sectioned", "chunked"].includes(extraction)) {
    return "Texto extraído";
  }
  return "Leitura em validação";
}

function normalizeMaterialReviewState(summary: BackendMaterialSummary): string {
  const extraction = summary.extraction_status.toLowerCase();

  if (extraction.includes("ocr") || summary.pipeline.has_ocr_warning) {
    return "OCR em validação";
  }
  if (summary.review_state === "ready_for_review" || summary.pipeline.ready_for_review) {
    return "Pronto para revisão";
  }
  return "Precisa de conferência";
}

function normalizeMaterialWarnings(summary: BackendMaterialSummary): string[] {
  const warnings = ["Este resumo mostra apenas metadados seguros do material."];
  if (summary.extraction_status.toLowerCase().includes("ocr") || summary.pipeline.has_ocr_warning) {
    warnings.push("PDFs escaneados podem exigir OCR e revisão adicional.");
    warnings.push("OCR em validação.");
  } else {
    warnings.push("Texto extraído sujeito a revisão.");
  }
  warnings.push(`${summary.warnings_count} avisos registrados para revisão.`);
  return warnings;
}

function buildMaterialDetailFromSummary(materialId: string, summary: BackendMaterialSummary): MaterialDetail {
  const listItem = mapProtectedMaterialItem({
    document_id: summary.document_id || materialId,
    display_filename: summary.display_filename,
    content_type: summary.content_type,
    material_type: summary.material_type,
    processing_status: summary.processing_status,
    status: summary.processing_status,
    extraction_status: summary.extraction_status,
    current_stage: summary.latest_pipeline_status ?? summary.pipeline.status ?? undefined,
    metadata_status: summary.review_state,
    review_state: summary.review_state,
    warnings_count: summary.warnings_count,
    latest_pipeline_status: summary.latest_pipeline_status,
    chunk_count: summary.chunk_count,
    section_count: summary.section_count
  });

  return {
    ...listItem,
    id: materialId,
    processingStatus: normalizeMaterialProcessingStatus(summary),
    extractionStatus: normalizeMaterialExtractionStatus(summary),
    reviewState: normalizeMaterialReviewState(summary),
    warnings: normalizeMaterialWarnings(summary),
    sectionPreviews:
      summary.section_count > 0 || summary.chunk_count > 0
        ? [
            {
              id: `${materialId}:summary`,
              title: "Estrutura segura identificada",
              level: 1,
              chunkRangeLabel: `${summary.section_count} seções · ${summary.chunk_count} trechos`
            }
          ]
        : [],
    sourceNote:
      "Resumo carregado por consulta protegida e apresentado sem texto bruto, OCR completo ou trechos do documento."
  };
}

export function buildMockMaterialsWorkspaceViewModel(): MaterialsWorkspaceViewModel {
  const items = cloneItems(materialsWorkspaceItems);
  return withMaterialTypeGrouping({
    connection: baseConnection(),
    summary: mockSummary(items),
    items
  });
}

export async function loadMaterialsWorkspaceViewModel(): Promise<MaterialsWorkspaceViewModel> {
  const config = getApiConfig();
  const fallback = buildMockMaterialsWorkspaceViewModel();

  if (config.forceMock) {
    return {
      ...fallback,
      connection: baseConnection({
        title: "Dados de demonstração",
        detail: "Esta área segue em dados de demonstração locais neste ambiente."
      })
    };
  }

  if (!config.baseUrl) {
    return {
      ...fallback,
      connection: baseConnection({
        detail: "A demonstração continua acessível enquanto a leitura protegida não está disponível."
      })
    };
  }

  const materialsResult = await fetchUserMaterialsList();
  if (!materialsResult.ok) {
    if (materialsResult.status === 401 || materialsResult.status === 403) {
      return {
        ...fallback,
        connection: {
          state: "auth_required",
          source: "backend",
          title: "Requer sessão",
          detail:
            "Entre para usar a listagem real de materiais. Enquanto isso, os dados de demonstração seguem disponíveis.",
          endpoint: "/api/materials"
        }
      };
    }
    return {
      ...fallback,
      connection: connectionFromFailure(materialsResult.source, materialsResult.error.message, "/api/materials")
    };
  }

  const items = materialsResult.data.items.map(mapProtectedMaterialItem);

  return withMaterialTypeGrouping({
    ...fallback,
    connection: {
      state: "connected",
      source: "backend",
      title: "Dados reais da sessão",
      detail:
        "A listagem abaixo mostra os materiais recentes da sua sessão.",
      endpoint: "/api/materials"
    },
    summary: workspaceSummary(
      materialsResult.data.processed_count,
      materialsResult.data.ocr_required_count,
      items.filter((item) => item.reviewState === "Pronto para revisão").length,
      items.reduce((total, item) => total + item.relatedGaps, 0)
    ),
    items
  });
}

export function buildMockMaterialDetail(materialId: string): MaterialDetail | null {
  const detail = materialDetailsById[materialId];
  return detail ? cloneDetail(detail) : null;
}

export async function loadMaterialDetail(materialId: string): Promise<{
  connection: BackendConnectionInfo;
  detail: MaterialDetail | null;
}> {
  const config = getApiConfig();
  const fallback = buildMockMaterialDetail(materialId);

  if (config.forceMock) {
    return {
      connection: baseConnection({
        title: "Dados de demonstração",
        detail: "Este material segue em dados de demonstração locais neste ambiente."
      }),
      detail: fallback
    };
  }

  if (!config.baseUrl) {
    return {
      connection: baseConnection({
        detail: "A demonstração continua acessível enquanto este material ainda não pode ser lido pela leitura protegida."
      }),
      detail: fallback
    };
  }

  const summaryResult = await fetchMaterialSummary(materialId);

  if (!summaryResult.ok) {
    if (summaryResult.status === 404) {
      return {
        connection: {
          state: "error",
          source: "backend",
          title: "Item não encontrado",
          detail: "Este conteúdo não está disponível nesta sessão.",
          endpoint: `/api/materials/${materialId}/summary`
        },
        detail: null
      };
    }
    if (summaryResult.status === 401 || summaryResult.status === 403) {
      return {
        connection: {
          state: "auth_required",
          source: "backend",
          title: "Requer sessão",
          detail: "Os detalhes reais do material exigem uma sessão válida para consulta protegida.",
          endpoint: `/api/materials/${materialId}/summary`
        },
        detail: fallback
      };
    }

    return {
      connection: connectionFromFailure(
        summaryResult.source,
        summaryResult.error.message,
        `/api/materials/${materialId}/summary`
      ),
      detail: fallback
    };
  }

  const detail = buildMaterialDetailFromSummary(materialId, summaryResult.data);

  return {
    connection: {
      state: "connected",
      source: "backend",
      title: "Dados reais da sessão",
      detail: "Este resumo do material usa metadados seguros da sua sessão.",
      endpoint: `/api/materials/${materialId}/summary`
    },
    detail
  };
}
