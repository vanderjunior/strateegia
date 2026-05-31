import { getApiConfig } from "@/lib/api/config";
import { fetchUserEditaisList } from "@/lib/api/editais";
import { fetchUserMaterialsList, normalizeMaterialType } from "@/lib/api/documents";
import type { ApiSource, BackendConnectionInfo, BackendProtectedEditaisListItem, MaterialType } from "@/lib/api/types";

export type EditalAnalysisState =
  | "no_edital_uploaded"
  | "edital_uploaded_not_analyzed"
  | "edital_analyzed"
  | "analysis_needs_review"
  | "analysis_unavailable";

export interface RealUserStudyReadiness {
  connection: BackendConnectionInfo;
  isAuthenticated: boolean;
  hasRealMaterials: boolean;
  hasRealEditalMaterial: boolean;
  hasRealStudyMaterial: boolean;
  hasAnalyzedEdital: boolean;
  editalAnalysisState: EditalAnalysisState;
  editalAnalysisLabel: string;
  editalAnalysisDescription: string;
  canShowConcreteStudyPlan: boolean;
  shouldShowEditalUploadCTA: boolean;
  shouldShowStudyMaterialCTA: boolean;
  materialsCount: number;
  editalMaterialsCount: number;
  studyMaterialsCount: number;
  materialTypeCounts: Record<MaterialType, number>;
}

const EMPTY_COUNTS: Record<MaterialType, number> = {
  edital: 0,
  study_material: 0,
  previous_exam: 0,
  bibliography: 0,
  note: 0,
  other: 0,
  unknown: 0
};

function baseConnection(source: ApiSource, title: string, detail: string): BackendConnectionInfo {
  return {
    state: source === "backend" ? "connected" : source === "offline" ? "offline" : source === "unsupported" ? "unsupported" : "mock",
    source,
    title,
    detail
  };
}

function editalAnalysisCopy(state: EditalAnalysisState): {
  label: string;
  description: string;
} {
  switch (state) {
    case "edital_uploaded_not_analyzed":
      return {
        label: "Edital enviado",
        description: "Edital recebido. A análise ainda não foi executada nesta versão."
      };
    case "edital_analyzed":
      return {
        label: "Edital analisado",
        description: "Edital analisado disponível para consulta."
      };
    case "analysis_needs_review":
      return {
        label: "Precisa de conferência",
        description: "Edital analisado, mas precisa de conferência antes de orientar o estudo."
      };
    case "analysis_unavailable":
      return {
        label: "Análise indisponível",
        description: "Não foi possível confirmar o estado da análise agora."
      };
    default:
      return {
        label: "Nenhum edital enviado",
        description: "Envie um edital para orientar seu caminho de estudo."
      };
  }
}

function editalItemNeedsReview(item: BackendProtectedEditaisListItem): boolean {
  const reviewState = item.review_state.toLowerCase();
  const coverageStatus = item.coverage_status.toLowerCase();
  const status = item.status.toLowerCase();

  const reviewIsReady =
    reviewState === "ready" ||
    reviewState === "ready_for_review" ||
    reviewState === "pronto para revisão";
  const coverageIsReady = coverageStatus === "good" || coverageStatus === "cobertura boa";
  const statusIsReady = status === "ready" || status === "pronto" || status === "analisado";

  if (reviewIsReady && coverageIsReady && statusIsReady) {
    return false;
  }

  return (
    (reviewState.includes("review") && !reviewIsReady) ||
    reviewState.includes("conferência") ||
    reviewState.includes("pending") ||
    reviewState.includes("preliminar") ||
    coverageStatus.includes("partial") ||
    coverageStatus.includes("gap") ||
    coverageStatus.includes("needs") ||
    coverageStatus.includes("review") ||
    status.includes("candidata") ||
    status.includes("preliminar")
  );
}

function editalAnalysisStateFromItem(item: BackendProtectedEditaisListItem): EditalAnalysisState {
  switch (item.analysis_status) {
    case "uploaded_not_analyzed":
    case "not_ready":
      return "edital_uploaded_not_analyzed";
    case "needs_review":
      return "analysis_needs_review";
    case "failed":
    case "unknown":
      return "analysis_unavailable";
    case "analyzed":
      return editalItemNeedsReview(item) ? "analysis_needs_review" : "edital_analyzed";
    default:
      return editalItemNeedsReview(item) ? "analysis_needs_review" : "edital_analyzed";
  }
}

export function buildDefaultRealUserStudyReadiness(
  overrides: Partial<RealUserStudyReadiness> = {}
): RealUserStudyReadiness {
  const materialTypeCounts = {
    ...EMPTY_COUNTS,
    ...(overrides.materialTypeCounts ?? {})
  };
  const editalAnalysisState = overrides.editalAnalysisState ?? "analysis_unavailable";
  const editalAnalysis = editalAnalysisCopy(editalAnalysisState);

  return {
    connection: baseConnection("mock", "Orientação de demonstração", "A orientação concreta depende das informações da sua conta."),
    isAuthenticated: false,
    hasRealMaterials: false,
    hasRealEditalMaterial: false,
    hasRealStudyMaterial: false,
    hasAnalyzedEdital: false,
    editalAnalysisState,
    editalAnalysisLabel: editalAnalysis.label,
    editalAnalysisDescription: editalAnalysis.description,
    canShowConcreteStudyPlan: false,
    shouldShowEditalUploadCTA: editalAnalysisState === "no_edital_uploaded" || editalAnalysisState === "analysis_unavailable",
    shouldShowStudyMaterialCTA:
      editalAnalysisState === "edital_uploaded_not_analyzed" ||
      editalAnalysisState === "edital_analyzed" ||
      editalAnalysisState === "analysis_needs_review",
    materialsCount: 0,
    editalMaterialsCount: 0,
    studyMaterialsCount: 0,
    ...overrides,
    materialTypeCounts
  };
}

export async function loadRealUserStudyReadiness(): Promise<RealUserStudyReadiness> {
  const config = getApiConfig();

  if (config.forceMock) {
    return buildDefaultRealUserStudyReadiness({
      editalAnalysisState: "analysis_unavailable",
      connection: baseConnection("mock", "Orientação de demonstração", "Dados de demonstração não montam um caminho real.")
    });
  }

  if (!config.baseUrl) {
    return buildDefaultRealUserStudyReadiness({
      editalAnalysisState: "analysis_unavailable",
      connection: baseConnection("unsupported", "Dados reais não carregados agora", "Configure a leitura real para montar o caminho de estudo.")
    });
  }

  const materialsResult = await fetchUserMaterialsList();

  if (!materialsResult.ok) {
    if (materialsResult.status === 401 || materialsResult.status === 403) {
      return buildDefaultRealUserStudyReadiness({
        editalAnalysisState: "analysis_unavailable",
        connection: {
          state: "auth_required",
          source: "backend",
          title: "Entre para carregar seus dados",
          detail: "A orientação real depende de uma sessão ativa."
        }
      });
    }

    return buildDefaultRealUserStudyReadiness({
      editalAnalysisState: "analysis_unavailable",
      connection: baseConnection(
        materialsResult.source,
        "Dados reais não carregados agora",
        "A orientação local continua disponível sem tratar demonstrações como seus dados."
      )
    });
  }

  const materialTypeCounts = { ...EMPTY_COUNTS };
  materialsResult.data.items.forEach((item) => {
    const materialType = normalizeMaterialType(item.material_type);
    materialTypeCounts[materialType] += 1;
  });

  const editaisResult = await fetchUserEditaisList();
  const editalMaterialsCount = materialTypeCounts.edital;
  const studyMaterialsCount = materialTypeCounts.study_material;
  const hasEditalMaterial = editalMaterialsCount > 0;

  let editalAnalysisState: EditalAnalysisState = hasEditalMaterial
    ? "edital_uploaded_not_analyzed"
    : "no_edital_uploaded";

  if (!editaisResult.ok) {
    editalAnalysisState =
      editaisResult.source === "offline" || editaisResult.source === "unsupported" || editaisResult.status === 401 || editaisResult.status === 403
        ? "analysis_unavailable"
        : editalAnalysisState;
  } else if (editaisResult.data.items.length > 0) {
    const itemStates = editaisResult.data.items.map(editalAnalysisStateFromItem);
    if (itemStates.includes("analysis_needs_review")) {
      editalAnalysisState = "analysis_needs_review";
    } else if (itemStates.includes("edital_analyzed")) {
      editalAnalysisState = "edital_analyzed";
    } else if (itemStates.includes("edital_uploaded_not_analyzed")) {
      editalAnalysisState = "edital_uploaded_not_analyzed";
    } else {
      editalAnalysisState = "analysis_unavailable";
    }
  }

  const hasAnalyzedEdital =
    editalAnalysisState === "edital_analyzed" || editalAnalysisState === "analysis_needs_review";
  const canShowConcreteStudyPlan = editalAnalysisState === "edital_analyzed";

  return buildDefaultRealUserStudyReadiness({
    connection: baseConnection("backend", "Informações da sua conta", "Estado baseado nos materiais e editais da sua conta."),
    isAuthenticated: true,
    hasRealMaterials: materialsResult.data.items.length > 0,
    hasRealEditalMaterial: hasEditalMaterial,
    hasRealStudyMaterial: studyMaterialsCount > 0,
    hasAnalyzedEdital,
    editalAnalysisState,
    canShowConcreteStudyPlan,
    shouldShowEditalUploadCTA: editalAnalysisState === "no_edital_uploaded" || editalAnalysisState === "analysis_unavailable",
    shouldShowStudyMaterialCTA:
      editalAnalysisState === "edital_uploaded_not_analyzed" ||
      editalAnalysisState === "edital_analyzed" ||
      editalAnalysisState === "analysis_needs_review",
    materialsCount: materialsResult.data.items.length,
    editalMaterialsCount,
    studyMaterialsCount,
    materialTypeCounts
  });
}
