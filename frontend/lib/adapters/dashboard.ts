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
    title: "Mock fallback ativo",
    detail:
      "O shell permanece utilizavel sem backend e exibe apenas o snapshot auditado das capacidades.",
    ...overrides
  };
}

export function buildMockDashboardViewModel(
  overrides: Partial<DashboardViewModel> = {}
): DashboardViewModel {
  return {
    connection: baseConnection(),
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
      title: "Materiais ativos",
      value: `${overview.materials.total_materials} materiais`,
      note: `${overview.materials.ocr_required_count} com OCR em validacao e ${overview.materials.pending_count} pendentes`,
      metric: Math.max(6, processedRatio)
    },
    {
      title: "Ciclo atual",
      value: overview.study_cycle.cycle_available
        ? `${overview.study_cycle.topic_slot_count} slots de topico`
        : "Ciclo ainda nao gerado",
      note: overview.study_cycle.cycle_available
        ? `Estado ${overview.study_cycle.status} com leitura ${overview.study_readiness}`
        : "Permanece guidance-only ate existir artefato do usuario",
      metric: overview.study_cycle.cycle_available ? 64 : 18
    },
    {
      title: "Simulado readiness",
      value: overview.simulado_blueprint.blueprint_available
        ? `${overview.simulado_blueprint.question_slot_count} slots de questoes`
        : "Blueprint ainda nao disponivel",
      note: overview.simulado_blueprint.blueprint_available
        ? `Estado ${overview.simulado_blueprint.readiness_state}`
        : "Foundation existe, mas o fluxo completo nao e automatico",
      metric: overview.simulado_blueprint.blueprint_available ? 71 : 22
    }
  ];
}

function enhanceDocumentCards(
  cards: CapabilityCard[],
  overview: BackendDashboardOverview
): CapabilityCard[] {
  return cards.map((card) => {
    if (card.title === "PDF textual") {
      return {
        ...card,
        detail: `${overview.document_pipeline.total_documents} documentos no pipeline atual, ${overview.document_pipeline.extracted_count} com extracao concluida.`
      };
    }
    if (card.title === "PDF escaneado / OCR") {
      return {
        ...card,
        detail: `${overview.materials.ocr_required_count} materiais ainda dependem de OCR ou validacao humana.`
      };
    }
    if (card.title === "Ingestao de edital") {
      return {
        ...card,
        detail: overview.edital.edital_available
          ? `Ha um edital disponivel para o usuario autenticado com estado ${overview.edital.status}.`
          : card.detail
      };
    }
    if (card.title === "Alinhamento bibliografico") {
      return {
        ...card,
        detail: overview.alignment.alignment_available
          ? `Alignment disponivel com ${overview.alignment.gaps_detected} gaps detectados.`
          : card.detail
      };
    }
    return card;
  });
}

function enhancePscppCards(cards: CapabilityCard[], profile: BackendExamProfile): CapabilityCard[] {
  return cards.map((card) => {
    if (card.title === "Question style profile") {
      return {
        ...card,
        detail: `Perfil publico lido do backend: ${profile.profile_name} (${profile.profile_id}).`
      };
    }
    if (card.title === "Question generation integration") {
      return {
        ...card,
        detail: "A integracao continua declarativa e segura; a UI usa metadata sem gerar respostas finais sensiveis."
      };
    }
    if (card.title === "Study cycle guide") {
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
      title: "Backend sem endpoint compativel",
      detail: message,
      endpoint
    });
  }
  if (source === "offline") {
    return baseConnection({
      state: "offline",
      source,
      title: "Backend offline ou indisponivel",
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

export async function loadDashboardViewModel(): Promise<DashboardViewModel> {
  const config = getApiConfig();
  if (config.forceMock) {
    return buildMockDashboardViewModel({
      connection: baseConnection({
        title: "Mock forçado por configuracao",
        detail: "NEXT_PUBLIC_USE_MOCK_API=true manteve o painel em modo local."
      })
    });
  }
  if (!config.baseUrl) {
    return buildMockDashboardViewModel({
      connection: baseConnection({
        detail: "Defina NEXT_PUBLIC_API_BASE_URL para habilitar leitura read-only do backend."
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
    title: "Backend conectado",
    detail: "Perfis publicos do backend foram carregados em modo read-only.",
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
      title: "Backend conectado com overview autenticado",
      detail: "O dashboard recebeu dados reais do overview do usuario sem abandonar o fallback local.",
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
      title: "Backend conectado, sessao necessaria",
      detail:
        "Os perfis publicos foram lidos do backend, mas o overview pessoal continua protegido ate existir sessao valida.",
      endpoint: "/api/dashboard/overview"
    };
  } else if (overviewResult.source === "unsupported") {
    connection = {
      state: "connected",
      source: "backend",
      title: "Backend conectado com surface parcial",
      detail: "Os endpoints publicos responderam, mas o overview nao esta disponivel nesta instalacao.",
      endpoint: "/api/dashboard/overview"
    };
  }

  return buildMockDashboardViewModel({
    connection,
    studyOverviewCards: overviewCards,
    documentCards: documents,
    pscppCards: enhancePscppCards(cloneCards(pscppProfileCards), pscppProfileResult.data),
    capabilityItems
  });
}
