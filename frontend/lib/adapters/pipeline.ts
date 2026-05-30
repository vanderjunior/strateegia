import { getApiConfig } from "@/lib/api/config";
import { fetchPipelineSummary } from "@/lib/api/pipeline";
import type {
  ApiSource,
  BackendConnectionInfo,
  BackendPipelineSummary,
  BackendPipelineSummaryStep,
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
    title: "Dados de demonstração",
    detail: "Demonstração exibida até existir leitura segura para este material.",
    ...overrides
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

function statusLabelForStep(step: BackendPipelineSummaryStep, hasOcrWarning: boolean): string {
  if (hasOcrWarning && step.key === "text_extracted") {
    return "OCR necessário";
  }
  if (hasOcrWarning && step.key === "ready_for_review") {
    return "OCR em validação";
  }
  if (step.state === "done") {
    return "Concluído";
  }
  if (step.state === "needs_review") {
    return "Revisão necessária";
  }
  return "Validação pendente";
}

function toneForStep(step: BackendPipelineSummaryStep, hasOcrWarning: boolean): PipelineStep["tone"] {
  if (hasOcrWarning && (step.key === "text_extracted" || step.key === "ready_for_review")) {
    return "warning";
  }
  if (step.state === "done") {
    return "complete";
  }
  if (step.state === "needs_review") {
    return "warning";
  }
  return "pending";
}

function detailForStep(step: BackendPipelineSummaryStep, hasOcrWarning: boolean): string {
  if (step.key === "uploaded") {
    return "Material já registrado para leitura controlada.";
  }
  if (step.key === "text_extracted") {
    return hasOcrWarning
      ? "A leitura textual ainda depende de OCR ou validação."
      : "A leitura textual foi preparada sem expor conteúdo bruto.";
  }
  if (step.key === "segmented") {
    return step.state === "done"
      ? "Trechos e seções já foram contabilizados para revisão."
      : "A segmentação ainda depende de validação.";
  }
  return step.state === "done"
    ? "O material já está em etapa de revisão."
    : "O material segue em preparação controlada para revisão.";
}

function buildSteps(summary: BackendPipelineSummary): PipelineStep[] {
  return summary.steps.map((step) => ({
    id: step.key,
    label: step.label,
    statusLabel: statusLabelForStep(step, summary.has_ocr_warning),
    tone: toneForStep(step, summary.has_ocr_warning),
    detail: detailForStep(step, summary.has_ocr_warning)
  }));
}

function extractionLabel(summary: BackendPipelineSummary): string {
  if (summary.has_ocr_warning || summary.status === "ocr_required") {
    return "OCR em validação";
  }
  if (["text_extracted", "segmented", "ready_for_review"].includes(summary.status)) {
    return "Texto extraído";
  }
  return "Validação pendente";
}

function reviewLabel(summary: BackendPipelineSummary): string {
  if (summary.ready_for_review || summary.status === "ready_for_review") {
    return "Pronto para revisão";
  }
  if (summary.has_ocr_warning || summary.status === "ocr_required") {
    return "OCR necessário";
  }
  return "Validação pendente";
}

export function buildMockPipelineDetail(documentId: string): PipelineDetailViewModel | null {
  const detail = pipelineDetailsById[documentId];
  return detail ? cloneViewModel(detail) : null;
}

export async function loadPipelineDetail(documentId: string): Promise<{
  connection: BackendConnectionInfo;
  detail: PipelineDetailViewModel | null;
}> {
  const config = getApiConfig();
  const fallback = buildMockPipelineDetail(documentId);

  if (config.forceMock) {
    return {
      connection: baseConnection({
        title: "Dados de demonstração",
        detail: "Este painel segue em dados de demonstração locais neste ambiente."
      }),
      detail: fallback
    };
  }

  if (!config.baseUrl) {
    return {
      connection: baseConnection({
        detail: "A demonstração continua acessível enquanto este acompanhamento ainda não pode ser lido pela leitura protegida."
      }),
      detail: fallback
    };
  }

  const pipelineResult = await fetchPipelineSummary(documentId);

  if (!pipelineResult.ok) {
    if (pipelineResult.status === 404) {
      return {
        connection: {
          state: "error",
          source: "backend",
          title: "Item não encontrado",
          detail: "Este conteúdo não está disponível nesta sessão.",
          endpoint: `/api/materials/${documentId}/pipeline/summary`
        },
        detail: null
      };
    }
    if (pipelineResult.status === 401 || pipelineResult.status === 403) {
      return {
        connection: {
          state: "auth_required",
          source: "backend",
          title: "Requer sessão",
          detail: "O pipeline real do material exige uma sessão válida para consulta protegida.",
          endpoint: `/api/materials/${documentId}/pipeline/summary`
        },
        detail: fallback
      };
    }
    return {
      connection: connectionFromFailure(
        pipelineResult.source,
        pipelineResult.error.message,
        `/api/materials/${documentId}/pipeline/summary`
      ),
      detail: fallback
    };
  }

  const summary = pipelineResult.data;
  const connection: BackendConnectionInfo = {
    state: "connected",
    source: "backend",
    title: "Dados reais da sessão",
    detail: "O pipeline foi consultado por resumo seguro e apresentado em linguagem de produto.",
    endpoint: `/api/materials/${documentId}/pipeline/summary`
  };

  return {
    connection,
    detail: {
      documentId,
      title: fallback?.title ?? "Pipeline em validação",
      source: "backend",
      extractionStatus: extractionLabel(summary),
      reviewState: reviewLabel(summary),
      sectionsCount: summary.section_count,
      chunksCount: summary.chunk_count,
      notes: summary.has_ocr_warning
        ? ["Este arquivo pode precisar de OCR antes da revisão."]
        : ["Texto extraído sujeito a revisão."],
      steps: buildSteps(summary),
      connection
    }
  };
}
