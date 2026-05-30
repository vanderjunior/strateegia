import { buildAuditedCapabilityItems } from "@/lib/api/capabilities";
import { getApiConfig } from "@/lib/api/config";
import { fetchPscppExamProfile } from "@/lib/api/pscpp";
import { fetchDashboardOverview } from "@/lib/api/runtime";
import type {
  ApiSource,
  BackendConnectionInfo,
  BackendDashboardOverview,
  BackendExamProfile,
  CapabilityCard,
  CapabilityStatusItem,
  DashboardViewModel,
  StudyOverviewCard
} from "@/lib/api/types";
import {
  documentStatusCards,
  pscppProfileCards,
  runtimeStatusCards,
  studyOverviewCards
} from "@/lib/mock/mentorium-demo-data";

function cloneCards<T>(items: readonly T[]): T[] {
  return items.map((item) => ({ ...item }));
}

function baseConnection(
  overrides: Partial<BackendConnectionInfo> = {}
): BackendConnectionInfo {
  return {
    state: "mock",
    source: "mock",
    title: "Dados de demonstração ativos",
    detail: "O painel permanece utilizável como orientação de demonstração.",
    ...overrides
  };
}

export function buildMockDashboardViewModel(
  overrides: Partial<DashboardViewModel> = {}
): DashboardViewModel {
  return {
    connection: baseConnection(),
    usesRealUserData: false,
    hasRealEditalContext: false,
    studyOverviewCards: cloneCards(studyOverviewCards),
    documentCards: cloneCards(documentStatusCards),
    pscppCards: cloneCards(pscppProfileCards),
    runtimeCards: cloneCards(runtimeStatusCards),
    capabilityItems: buildAuditedCapabilityItems("mock"),
    ...overrides
  };
}

function buildOverviewCardsFromBackend(overview: BackendDashboardOverview): StudyOverviewCard[] {
  const processedRatio =
    overview.materials.total_materials > 0
      ? Math.round((overview.materials.processed_count / overview.materials.total_materials) * 100)
      : 0;

  return [
    {
      id: "dashboard-materials-active",
      title: "Materiais ativos",
      value: `${overview.materials.total_materials} materiais`,
      note: `${overview.materials.ocr_required_count} com OCR em validação e ${overview.materials.pending_count} pendentes`,
      metric: Math.max(6, processedRatio)
    },
    {
      id: "dashboard-cycle-current",
      title: "Ciclo atual",
      value: overview.study_cycle.cycle_available
        ? `${overview.study_cycle.topic_slot_count} blocos sugeridos`
        : "Ciclo ainda não sugerido",
      note: overview.study_cycle.cycle_available
        ? "Ciclo sugerido disponível para consulta, com leitura flexível do momento atual."
        : "Permanece como sugestão até existir um ciclo confirmado para o usuário",
      metric: overview.study_cycle.cycle_available ? 64 : 18
    },
    {
      id: "dashboard-simulado-readiness",
      title: "Simulado em preparação",
      value: overview.simulado_blueprint.blueprint_available
        ? `${overview.simulado_blueprint.question_slot_count} questões candidatas`
        : "Estrutura ainda não disponível",
      note: overview.simulado_blueprint.blueprint_available
        ? "Questões candidatas organizadas para revisão, ainda sem execução automática."
        : "A base existe, mas o fluxo completo ainda não é automático",
      metric: overview.simulado_blueprint.blueprint_available ? 71 : 22
    }
  ];
}

function enhanceDocumentCards(
  cards: CapabilityCard[],
  overview: BackendDashboardOverview
): CapabilityCard[] {
  return cards.map((card) => {
    if (card.internalKey === "pdf_text_extraction") {
      return {
        ...card,
        detail: `${overview.document_pipeline.total_documents} documentos no fluxo atual, ${overview.document_pipeline.extracted_count} com extração concluída.`
      };
    }
    if (card.internalKey === "ocr_adapter") {
      return {
        ...card,
        detail: `${overview.materials.ocr_required_count} materiais ainda dependem de OCR ou validação humana.`
      };
    }
    if (card.internalKey === "edital_ingestion") {
      return {
        ...card,
        detail: overview.edital.edital_available
          ? `Há um edital disponível para o usuário autenticado com estado ${overview.edital.status}.`
          : card.detail
      };
    }
    if (card.internalKey === "bibliography_alignment") {
      return {
        ...card,
        detail: overview.alignment.alignment_available
          ? `Alinhamento disponível com ${overview.alignment.gaps_detected} gaps detectados.`
          : card.detail
      };
    }
    return card;
  });
}

function enhancePscppCards(cards: CapabilityCard[], profile: BackendExamProfile): CapabilityCard[] {
  return cards.map((card) => {
    if (card.internalKey === "pscpp_question_style_profile") {
      return {
        ...card,
        detail: `Perfil público lido do backend: ${profile.profile_name} (${profile.profile_id}).`
      };
    }
    if (card.internalKey === "question_generation_blueprint") {
      return {
        ...card,
        detail: "A integração continua declarativa e segura; a interface usa metadados sem gerar respostas finais sensíveis."
      };
    }
    if (card.internalKey === "pscpp_study_cycle_profile") {
      return {
        ...card,
        detail: "Ainda sem endpoint dedicado; o frontend preserva fallback local auditado para o ciclo PSCPP."
      };
    }
    return card;
  });
}

function connectionFromFailure(source: ApiSource, message: string, endpoint: string): BackendConnectionInfo {
  if (source === "unsupported") {
    return baseConnection({
      state: "unsupported",
      source,
      title: "Dados reais indisponíveis agora",
      detail: "A orientação local continua disponível enquanto esta leitura é validada.",
      endpoint
    });
  }
  if (source === "offline") {
    return baseConnection({
      state: "offline",
      source,
      title: "Dados reais indisponíveis agora",
      detail: "Usando orientação local de demonstração até a conexão voltar.",
      endpoint
    });
  }
  return baseConnection({
    state: "mock",
    source,
    title: "Dados de demonstração ativos",
    detail: message,
    endpoint
  });
}

export async function loadDashboardViewModel(): Promise<DashboardViewModel> {
  const config = getApiConfig();
  if (config.forceMock) {
    return buildMockDashboardViewModel({
      connection: baseConnection({
        title: "Modo de demonstração ativo",
        detail: "A configuração local manteve o painel em modo de demonstração."
      })
    });
  }
  if (!config.baseUrl) {
    return buildMockDashboardViewModel({
      connection: baseConnection({
        detail: "A URL do backend ainda não foi configurada para leitura real."
      })
    });
  }

  const pscppProfileResult = await fetchPscppExamProfile();
  if (!pscppProfileResult.ok) {
    return buildMockDashboardViewModel({
      connection: connectionFromFailure(
        pscppProfileResult.source,
        pscppProfileResult.error.message,
        "/api/exam-profiles/exam-profile:marinha-pscpp"
      ),
      capabilityItems: buildAuditedCapabilityItems("mock")
    });
  }

  let connection = baseConnection({
    state: "connected",
    source: "backend",
    title: "Dados reais disponíveis",
    detail: "Perfis públicos do backend foram carregados em modo de consulta.",
    endpoint: "/api/exam-profiles/exam-profile:marinha-pscpp"
  });

  let capabilityItems: CapabilityStatusItem[] = buildAuditedCapabilityItems("mock").map((item) =>
    item.id === "pscpp-style"
      ? {
          ...item,
          source: "backend",
          detail: `Perfil ${pscppProfileResult.data.profile_name} lido do backend.`
        }
      : item
  );

  let overviewCards = cloneCards(studyOverviewCards);
  let documents = cloneCards(documentStatusCards);

  const overviewResult = await fetchDashboardOverview();
  if (overviewResult.ok) {
    connection = {
      state: "connected",
      source: "backend",
      title: "Dados reais com sessão ativa",
      detail: "O dashboard recebeu dados reais da visão do usuário sem abandonar o fallback local.",
      endpoint: "/api/dashboard/overview"
    };
    overviewCards = buildOverviewCardsFromBackend(overviewResult.data);
    documents = enhanceDocumentCards(documents, overviewResult.data);
    capabilityItems = capabilityItems.map((item) => {
      if (["text-pdf", "scanned-ocr", "edital-ingestion", "bibliography-alignment", "simulado-generation"].includes(item.id)) {
        return {
          ...item,
          source: "backend"
        };
      }
      return item;
    });
  } else if (overviewResult.status === 401) {
    connection = {
      state: "auth_required",
      source: "backend",
      title: "Dados reais exigem sessão",
      detail:
        "Os perfis públicos foram lidos do backend, mas a visão pessoal continua protegida até existir sessão válida.",
      endpoint: "/api/dashboard/overview"
    };
  } else if (overviewResult.source === "unsupported") {
    connection = {
      state: "connected",
      source: "backend",
      title: "Dados reais parcialmente carregados",
      detail: "Os perfis principais responderam, mas esta visão ainda não está disponível neste ambiente.",
      endpoint: "/api/dashboard/overview"
    };
  }

  return buildMockDashboardViewModel({
    connection,
    usesRealUserData: overviewResult.ok,
    hasRealEditalContext: overviewResult.ok ? overviewResult.data.edital.edital_available : false,
    studyOverviewCards: overviewCards,
    documentCards: documents,
    pscppCards: enhancePscppCards(cloneCards(pscppProfileCards), pscppProfileResult.data),
    capabilityItems
  });
}
