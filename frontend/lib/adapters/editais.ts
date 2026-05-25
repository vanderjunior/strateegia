import { getApiConfig } from "@/lib/api/config";
import { fetchEditalAlignment, fetchEditalById } from "@/lib/api/editais";
import { fetchDashboardOverview } from "@/lib/api/runtime";
import type {
  ApiSource,
  BackendBibliographyAlignment,
  BackendConnectionInfo,
  BackendEditalExtraction,
  CoverageItem,
  EditalDetail,
  EditaisWorkspaceViewModel,
  EditalListItem,
  GapItem,
  WorkspaceSummaryMetric
} from "@/lib/api/types";
import {
  editalCoverageItems,
  editalDetailsById,
  editalGapItems,
  editaisWorkspaceItems
} from "@/lib/mock/mentorium-demo-data";
import { getUserFacingCapability } from "@/lib/product/product-language";

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
    title: "Usando dados de demonstração",
    detail: "A listagem permanece em modo de demonstração até existir leitura segura de editais para esta área.",
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

function mapCoverageItem(coverage: BackendBibliographyAlignment["topic_coverage"][number]): CoverageItem {
  let coverageLabel = "Cobertura parcial";
  if (coverage.coverage_state === "covered") {
    coverageLabel = "Cobertura boa";
  } else if (coverage.coverage_state === "uncovered") {
    coverageLabel = "Gap encontrado";
  } else if (coverage.coverage_state === "weakly_covered") {
    coverageLabel = "Precisa de material";
  }

  return {
    id: coverage.topic_id,
    title: coverage.topic_title,
    coverageLabel,
    detail: "Alinhamento preliminar sujeito a revisão.",
    source: "backend"
  };
}

function mapGapItem(gap: BackendBibliographyAlignment["gaps"][number]): GapItem {
  let detail = "Gap encontrado em alinhamento preliminar.";
  let severityLabel = "Revisão necessária";

  if (gap.gap_type === "ocr_required") {
    detail = "O tópico depende de OCR ou revisão adicional antes de seguir.";
    severityLabel = "OCR necessário";
  } else if (gap.gap_type === "missing_bibliography_material") {
    detail = "Ainda falta material para cobrir este ponto com segurança.";
    severityLabel = "Precisa de material";
  }

  return {
    id: gap.gap_id,
    title: gap.target_title,
    detail,
    severityLabel,
    source: "backend"
  };
}

function buildDetailFromBackend(
  editalId: string,
  edital: BackendEditalExtraction,
  alignment?: BackendBibliographyAlignment
): EditalDetail {
  const fallback = editalDetailsById[editalId];
  const coverageItems = alignment?.topic_coverage.length
    ? alignment.topic_coverage.slice(0, 6).map(mapCoverageItem)
    : cloneCoverage(editalCoverageItems);
  const gapItems = alignment?.gaps.length
    ? alignment.gaps.slice(0, 6).map(mapGapItem)
    : cloneGaps(editalGapItems);

  return {
    id: editalId,
    title: fallback?.title ?? getUserFacingCapability("edital_ingestion", "student")?.label ?? "Edital analisado",
    statusLabel: "Análise candidata",
    topicsCount: edital.topics.length,
    bibliographyItemsCount: edital.bibliography.length,
    gapsCount: gapItems.length,
    reviewState:
      edital.warnings.length || gapItems.length ? "Precisa de conferência" : "Pronto para revisão",
    source: "backend",
    topicCandidates: edital.topics.slice(0, 8).map((topic) => topic.title),
    bibliographyCandidates: edital.bibliography
      .slice(0, 8)
      .map((item) => item.title?.trim() || item.raw_reference),
    coverageItems,
    gapItems,
    warnings: [
      "Os tópicos exibidos são candidatos e ainda precisam de conferência.",
      ...edital.warnings.slice(0, 3).map((warning) => warning.message)
    ],
    notes: [
      "Alinhamento preliminar sujeito a revisão.",
      "A bibliografia apresentada não deve ser tratada como verdade final sem conferência humana."
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
        title: "Mock forçado por configuração",
        detail: "NEXT_PUBLIC_USE_MOCK_API=true manteve esta área em modo local."
      })
    };
  }

  if (!config.baseUrl) {
    return {
      ...fallback,
      connection: baseConnection({
        detail: "Defina NEXT_PUBLIC_API_BASE_URL para habilitar leituras read-only autenticadas quando existirem."
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
            "O backend está disponível, mas a visão de editais continua protegida até existir uma sessão válida no navegador.",
          endpoint: "/api/dashboard/overview"
        }
      };
    }
    return {
      ...fallback,
      connection: connectionFromFailure(overviewResult.source, overviewResult.error.message, "/api/dashboard/overview")
    };
  }

  const topicsFromMock = fallback.items.reduce((total, item) => total + item.topicsCount, 0);
  const bibliographyFromMock = fallback.items.reduce((total, item) => total + item.bibliographyItemsCount, 0);

  return {
    ...fallback,
    connection: {
      state: "connected",
      source: "backend",
      title: "Backend conectado com fallback auditado",
      detail:
        "Os sinais de edital e gaps vieram do backend em modo somente leitura. A listagem detalhada ainda usa dados de demonstração seguros.",
      endpoint: "/api/dashboard/overview"
    },
    summary: buildSummary(
      overviewResult.data.edital.edital_available ? 1 : fallback.items.length,
      topicsFromMock,
      bibliographyFromMock,
      overviewResult.data.alignment.gaps_detected,
      overviewResult.data.alignment.gaps_detected > 0 ? 1 : fallback.items.length
    )
  };
}

export function buildMockEditalDetail(editalId: string): EditalDetail {
  const detail = editalDetailsById[editalId] ?? {
    id: editalId,
    title: "Edital em validação",
    statusLabel: "Análise candidata",
    topicsCount: 0,
    bibliographyItemsCount: 0,
    gapsCount: 0,
    reviewState: "Precisa de conferência",
    source: "mock" as const,
    topicCandidates: [],
    bibliographyCandidates: [],
    coverageItems: cloneCoverage(editalCoverageItems),
    gapItems: cloneGaps(editalGapItems),
    warnings: ["Nenhum detalhe adicional disponível ainda."],
    notes: ["Alinhamento preliminar sujeito a revisão."]
  };

  return cloneDetail(detail);
}

export async function loadEditalDetail(editalId: string): Promise<{
  connection: BackendConnectionInfo;
  detail: EditalDetail;
}> {
  const config = getApiConfig();
  const fallback = buildMockEditalDetail(editalId);

  if (config.forceMock) {
    return {
      connection: baseConnection({
        title: "Mock forçado por configuração",
        detail: "NEXT_PUBLIC_USE_MOCK_API=true manteve este edital em modo local."
      }),
      detail: fallback
    };
  }

  if (!config.baseUrl) {
    return {
      connection: baseConnection({
        detail: "Defina NEXT_PUBLIC_API_BASE_URL para tentar ler este edital em modo somente leitura."
      }),
      detail: fallback
    };
  }

  const editalResult = await fetchEditalById(editalId);
  if (!editalResult.ok) {
    if (editalResult.status === 401) {
      return {
        connection: {
          state: "auth_required",
          source: "backend",
          title: "Sessão necessária",
          detail: "Os detalhes reais do edital exigem uma sessão válida para leitura em modo somente leitura.",
          endpoint: `/api/edital/${editalId}`
        },
        detail: fallback
      };
    }
    return {
      connection: connectionFromFailure(editalResult.source, editalResult.error.message, `/api/edital/${editalId}`),
      detail: fallback
    };
  }

  const alignmentResult = await fetchEditalAlignment(editalId);
  const detail = buildDetailFromBackend(
    editalId,
    editalResult.data,
    alignmentResult.ok ? alignmentResult.data : undefined
  );

  return {
    connection: {
      state: "connected",
      source: "backend",
      title: "Detalhes carregados do backend",
      detail: "Este edital foi lido em modo somente leitura e continua marcado como análise preliminar.",
      endpoint: `/api/edital/${editalId}`
    },
    detail
  };
}
