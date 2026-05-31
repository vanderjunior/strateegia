import { getApiConfig } from "@/lib/api/config";
import { fetchEditalSummary, fetchUserEditaisList } from "@/lib/api/editais";
import type {
  ApiSource,
  BackendConnectionInfo,
  BackendEditalSummary,
  BackendProtectedEditaisListItem,
  CoverageItem,
  EditalDetail,
  EditaisWorkspaceViewModel,
  EditalListItem,
  GapItem,
  WorkspaceSummaryMetric
} from "@/lib/api/types";
import {
  editalDetailsById,
  editaisWorkspaceItems
} from "@/lib/mock/mentorium-demo-data";

function cloneItems<T>(items: readonly T[]): T[] {
  return items.map((item) => ({ ...item }));
}

function cloneCoverage(items: readonly CoverageItem[]): CoverageItem[] {
  return items.map((item) => ({ ...item }));
}

function cloneGaps(items: readonly GapItem[]): GapItem[] {
  return items.map((item) => ({ ...item }));
}

function cloneDetail(detail: EditalDetail): EditalDetail {
  return {
    ...detail,
    topicCandidates: [...detail.topicCandidates],
    bibliographyCandidates: [...detail.bibliographyCandidates],
    coverageItems: cloneCoverage(detail.coverageItems),
    gapItems: cloneGaps(detail.gapItems),
    warnings: [...detail.warnings],
    notes: [...detail.notes]
  };
}

function baseConnection(overrides: Partial<BackendConnectionInfo> = {}): BackendConnectionInfo {
  return {
    state: "mock",
    source: "mock",
    title: "Dados de demonstração",
    detail: "Demonstração exibida até existir leitura segura de editais para esta área.",
    ...overrides
  };
}

function buildSummary(
  analyzed: number,
  topics: number,
  bibliography: number,
  gaps: number,
  reviewItems: number
): WorkspaceSummaryMetric[] {
  return [
    {
      id: "editais-analisados",
      label: "Editais analisados",
      value: String(analyzed),
      detail: "Leituras preliminares disponíveis para revisão."
    },
    {
      id: "editais-topicos",
      label: "Tópicos candidatos",
      value: String(topics),
      detail: "Tópicos identificados em leitura preliminar."
    },
    {
      id: "editais-bibliografia",
      label: "Bibliografia identificada",
      value: String(bibliography),
      detail: "Referências encontradas para conferência humana."
    },
    {
      id: "editais-gaps",
      label: "Gaps encontrados",
      value: String(gaps),
      detail: "Pontos que ainda exigem cobertura ou material complementar."
    },
    {
      id: "editais-review",
      label: "Itens para conferência",
      value: String(reviewItems),
      detail: "Itens que devem ser revistos antes de serem tratados como definitivos."
    }
  ];
}

function mockSummary(items: EditalListItem[]): WorkspaceSummaryMetric[] {
  return buildSummary(
    items.length,
    items.reduce((total, item) => total + item.topicsCount, 0),
    items.reduce((total, item) => total + item.bibliographyItemsCount, 0),
    items.reduce((total, item) => total + item.gapsCount, 0),
    items.filter((item) => item.reviewState !== "Pronto para revisão").length
  );
}

function editalStatusLabel(item: BackendProtectedEditaisListItem): string {
  switch (item.analysis_status) {
    case "not_ready":
    case "uploaded_not_analyzed":
      return "Edital recebido";
    case "analyzed":
      return "Edital analisado";
    case "needs_review":
      return "Edital analisado, mas precisa de conferência";
    case "failed":
      return "Não foi possível analisar este edital";
    default:
      return item.status === "analyzed" ? "Edital analisado" : "Análise indisponível";
  }
}

function editalReviewLabel(item: BackendProtectedEditaisListItem): string {
  switch (item.analysis_status) {
    case "not_ready":
    case "uploaded_not_analyzed":
      return "Análise ainda não concluída";
    case "analyzed":
      return reviewLabelForState(item.review_state);
    case "needs_review":
      return "Precisa de conferência";
    case "failed":
      return "Análise indisponível";
    default:
      return reviewLabelForState(item.review_state);
  }
}

function isNotReadyAnalysisStatus(value: BackendProtectedEditaisListItem["analysis_status"]): boolean {
  return value === "not_ready" || value === "uploaded_not_analyzed";
}

function mapProtectedEditalItem(item: BackendProtectedEditaisListItem): EditalListItem {
  const notReady = isNotReadyAnalysisStatus(item.analysis_status);

  return {
    id: item.edital_id,
    title: notReady ? "Edital recebido" : item.title,
    analysisStatus: item.analysis_status,
    statusLabel: editalStatusLabel(item),
    topicsCount: item.topics_count,
    bibliographyItemsCount: item.bibliography_count,
    gapsCount: item.gaps_count,
    reviewState: editalReviewLabel(item),
    source: "backend"
  };
}

function connectionFromFailure(source: ApiSource, message: string, endpoint: string): BackendConnectionInfo {
  if (source === "unsupported") {
    return baseConnection({
      state: "unsupported",
      source,
      title: "Demonstração",
      detail: "Esta área segue em demonstração enquanto seus editais não estão disponíveis.",
      endpoint
    });
  }
  if (source === "offline") {
    return baseConnection({
      state: "offline",
      source,
      title: "Dados indisponíveis",
      detail: "Não foi possível carregar seus editais agora. Você pode tentar novamente em instantes.",
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

function reviewLabelForState(value: string): string {
  if (value === "ready_for_review") {
    return "Pronto para revisão";
  }
  if (value === "pending") {
    return "Alinhamento preliminar";
  }
  return "Precisa de conferência";
}

function coverageLabelForState(value: string): string {
  if (value === "good") {
    return "Cobertura boa";
  }
  if (value === "gap_found") {
    return "Gap encontrado";
  }
  if (value === "needs_material") {
    return "Precisa de material";
  }
  if (value === "partial") {
    return "Cobertura parcial";
  }
  return "Alinhamento preliminar";
}

function alignmentLabelForState(value: string): string {
  if (value === "aligned") {
    return "Cobertura boa";
  }
  if (value === "partial") {
    return "Cobertura parcial";
  }
  if (value === "needs_review") {
    return "Revisão necessária";
  }
  if (value === "not_available") {
    return "Precisa de conferência";
  }
  return "Alinhamento preliminar";
}

function buildDetailFromSummary(editalId: string, summary: BackendEditalSummary): EditalDetail {
  const reviewState = reviewLabelForState(summary.review_state);
  const coverageLabel = coverageLabelForState(summary.coverage_status);
  const alignmentLabel = alignmentLabelForState(summary.alignment_status);
  const statusLabel =
    summary.analysis_status === "not_ready" || summary.analysis_status === "uploaded_not_analyzed"
      ? "Edital recebido"
      : summary.analysis_status === "analyzed"
        ? "Edital analisado"
        : summary.analysis_status === "needs_review"
          ? "Edital analisado, mas precisa de conferência"
          : summary.analysis_status === "failed"
            ? "Não foi possível analisar este edital"
            : "Análise indisponível";
  const safeReviewState =
    summary.analysis_status === "not_ready" || summary.analysis_status === "uploaded_not_analyzed"
      ? "Análise ainda não concluída"
      : summary.analysis_status === "failed"
        ? "Análise indisponível"
        : reviewState;
  const notReady = summary.analysis_status === "not_ready" || summary.analysis_status === "uploaded_not_analyzed";

  return {
    id: editalId,
    title: notReady ? "Edital recebido" : summary.title || "Edital analisado",
    analysisStatus: summary.analysis_status,
    statusLabel,
    topicsCount: summary.topics_count,
    bibliographyItemsCount: summary.bibliography_count,
    gapsCount: summary.gaps_count,
    reviewState: safeReviewState,
    source: "backend",
    topicCandidates: !notReady && summary.summary.has_topics
      ? [`${summary.topics_count} tópicos candidatos identificados`]
      : [],
    bibliographyCandidates: !notReady && summary.summary.has_bibliography
      ? [`${summary.bibliography_count} referências identificadas para conferência`]
      : [],
    coverageItems: notReady
      ? []
      : [
          {
            id: `${summary.edital_id}:coverage`,
            title: "Cobertura do edital",
            coverageLabel,
            detail: "Resumo de cobertura sujeito a revisão.",
            source: "backend"
          },
          {
            id: `${summary.edital_id}:alignment`,
            title: "Alinhamento da bibliografia",
            coverageLabel: alignmentLabel,
            detail: "Alinhamento sem evidências ou trechos brutos nesta tela.",
            source: "backend"
          }
        ],
    gapItems: !notReady && summary.summary.has_gaps
      ? [
          {
            id: `${summary.edital_id}:gaps`,
            title: `${summary.gaps_count} gaps encontrados`,
            detail: "Os gaps indicam pontos que precisam de cobertura ou conferência antes de orientar o estudo.",
            severityLabel: "Revisão necessária",
            source: "backend"
          }
        ]
      : [],
    warnings: [
      notReady
        ? "Este edital foi recebido, mas ainda não há tópicos ou bibliografia prontos para orientar o estudo."
        : "Este resumo mostra apenas informações organizadas do edital.",
      notReady
        ? "Confira se o arquivo tem texto extraível ou envie uma versão textual."
        : summary.summary.needs_review
        ? "A análise candidata precisa de conferência antes de orientar decisões finais."
        : "Mesmo quando pronto para revisão, o edital deve ser conferido antes de uso final.",
      `${summary.warnings_count} avisos registrados para revisão.`
    ],
    notes: [
      notReady ? "Análise ainda não concluída." : "Alinhamento preliminar sujeito a revisão.",
      "Esta tela não exibe texto bruto, evidências ou bibliografia completa do edital."
    ]
  };
}

export function buildMockEditaisWorkspaceViewModel(): EditaisWorkspaceViewModel {
  const items = cloneItems(editaisWorkspaceItems);
  return {
    connection: baseConnection(),
    summary: mockSummary(items),
    items
  };
}

export async function loadEditaisWorkspaceViewModel(): Promise<EditaisWorkspaceViewModel> {
  const config = getApiConfig();
  const fallback = buildMockEditaisWorkspaceViewModel();

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
        detail: "A demonstração continua acessível enquanto seus editais não estão disponíveis."
      })
    };
  }

  const editaisResult = await fetchUserEditaisList();
  if (!editaisResult.ok) {
    if (editaisResult.status === 401 || editaisResult.status === 403) {
      return {
        ...fallback,
        connection: {
          state: "auth_required",
          source: "backend",
          title: "Requer sessão",
          detail:
            "Entre para ver seus editais analisados.",
          endpoint: "/api/editais"
        }
      };
    }
    return {
      ...fallback,
      connection: connectionFromFailure(editaisResult.source, editaisResult.error.message, "/api/editais")
    };
  }

  const items = editaisResult.data.items.map(mapProtectedEditalItem);

  return {
    ...fallback,
    connection: {
      state: "connected",
      source: "backend",
      title: "Editais analisados",
      detail: "A listagem abaixo mostra editais analisados disponíveis para consulta.",
      endpoint: "/api/editais"
    },
    summary: buildSummary(
      editaisResult.data.total_editais,
      editaisResult.data.total_topics,
      editaisResult.data.total_bibliography_items,
      editaisResult.data.total_gaps,
      items.filter((item) => item.reviewState !== "Pronto para revisão").length
    ),
    items
  };
}

export function buildMockEditalDetail(editalId: string): EditalDetail | null {
  const detail = editalDetailsById[editalId];
  return detail ? cloneDetail(detail) : null;
}

export async function loadEditalDetail(editalId: string): Promise<{
  connection: BackendConnectionInfo;
  detail: EditalDetail | null;
}> {
  const config = getApiConfig();
  const fallback = buildMockEditalDetail(editalId);

  if (config.forceMock) {
    return {
      connection: baseConnection({
        title: "Dados de demonstração",
        detail: "Este edital segue em dados de demonstração locais neste ambiente."
      }),
      detail: fallback
    };
  }

  if (!config.baseUrl) {
    return {
      connection: baseConnection({
        detail: "Os exemplos continuam acessíveis enquanto este edital não carrega dados reais."
      }),
      detail: fallback
    };
  }

  const editalResult = await fetchEditalSummary(editalId);
  if (!editalResult.ok) {
    if (editalResult.status === 404) {
      return {
        connection: {
          state: "error",
          source: "backend",
          title: "Item não encontrado",
          detail: "Este conteúdo não está disponível nesta sessão.",
          endpoint: `/api/editais/${editalId}/summary`
        },
        detail: null
      };
    }
    if (editalResult.status === 401 || editalResult.status === 403) {
      return {
        connection: {
          state: "auth_required",
          source: "backend",
          title: "Requer sessão",
          detail: "Entre para ver os detalhes deste edital.",
          endpoint: `/api/editais/${editalId}/summary`
        },
        detail: fallback
      };
    }
    return {
      connection: connectionFromFailure(
        editalResult.source,
        editalResult.error.message,
        `/api/editais/${editalId}/summary`
      ),
      detail: fallback
    };
  }

  const detail = buildDetailFromSummary(editalId, editalResult.data);

  return {
    connection: {
      state: "connected",
      source: "backend",
      title: "Informações da sua conta",
      detail: detail.analysisStatus === "not_ready" || detail.analysisStatus === "uploaded_not_analyzed"
        ? "Este edital foi recebido, mas a análise ainda não está concluída."
        : "Este resumo do edital usa informações organizadas da sua conta e continua sujeito a revisão.",
      endpoint: `/api/editais/${editalId}/summary`
    },
    detail
  };
}
