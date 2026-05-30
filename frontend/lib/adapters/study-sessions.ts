import { fetchPscppExamProfile } from "@/lib/api/pscpp";
import type {
  ApiSource,
  BackendConnectionInfo,
  StudySessionDetail,
  StudySessionWorkspaceViewModel
} from "@/lib/api/types";
import {
  studySessionDetailsById,
  studySessionWorkspaceViewModelMock
} from "@/lib/mock/mentorium-demo-data";

function cloneConnection(connection: BackendConnectionInfo): BackendConnectionInfo {
  return { ...connection };
}

function sourceConnection(
  source: ApiSource,
  title: string,
  detail: string,
  state: BackendConnectionInfo["state"]
): BackendConnectionInfo {
  return {
    source,
    title,
    detail,
    state
  };
}

export function buildMockStudySessionWorkspaceViewModel(): StudySessionWorkspaceViewModel {
  return {
    ...studySessionWorkspaceViewModelMock,
    connection: cloneConnection(studySessionWorkspaceViewModelMock.connection),
    sessions: [...studySessionWorkspaceViewModelMock.sessions],
    highlightedGaps: [...studySessionWorkspaceViewModelMock.highlightedGaps],
    starterMaterials: [...studySessionWorkspaceViewModelMock.starterMaterials]
  };
}

export function buildMockStudySessionDetail(sessionId: string): StudySessionDetail | null {
  const detail = studySessionDetailsById[sessionId];
  return detail
    ? {
        ...detail,
        structure: [...detail.structure],
        relatedMaterials: [...detail.relatedMaterials],
        relatedEditais: [...detail.relatedEditais],
        relatedGaps: [...detail.relatedGaps],
        checklist: [...detail.checklist],
        outputs: [...detail.outputs],
        cautions: [...detail.cautions]
      }
    : null;
}

export async function loadStudySessionWorkspaceViewModel(): Promise<StudySessionWorkspaceViewModel> {
  const fallback = buildMockStudySessionWorkspaceViewModel();
  const result = await fetchPscppExamProfile();

  if (result.ok) {
    return {
      ...fallback,
      connection: sourceConnection(
        "backend",
        "Dados reais disponíveis",
        "Sessões sugeridas confirmadas pelo perfil PSCPP, mantendo o fluxo como guia de consulta.",
        "connected"
      )
    };
  }

  if (result.source === "offline") {
    return {
      ...fallback,
      connection: sourceConnection(
        "offline",
        "Dados reais não carregados agora",
        "Orientação de demonstração disponível enquanto os dados reais não estão disponíveis.",
        "offline"
      )
    };
  }

  if (result.source === "unsupported") {
    return {
      ...fallback,
      connection: sourceConnection(
        "unsupported",
        "Demonstração",
        "O perfil PSCPP não pôde ser confirmado neste ambiente; as sessões seguem em orientação de demonstração.",
        "unsupported"
      )
    };
  }

  return fallback;
}

export async function loadStudySessionDetail(sessionId: string): Promise<StudySessionDetail | null> {
  const detail = buildMockStudySessionDetail(sessionId);
  const result = await fetchPscppExamProfile();

  if (!detail) {
    return null;
  }

  if (result.ok || result.source === "offline" || result.source === "unsupported") {
    return detail;
  }

  return detail;
}
