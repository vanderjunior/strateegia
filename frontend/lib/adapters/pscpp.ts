import { fetchPscppExamProfile } from "@/lib/api/pscpp";
import type {
  ApiSource,
  BackendConnectionInfo,
  BackendExamProfile,
  PscppCycleViewModel,
  PscppQuestionsViewModel,
  PscppWorkspaceViewModel
} from "@/lib/api/types";
import {
  pscppCycleViewModelMock,
  pscppQuestionsViewModelMock,
  pscppWorkspaceViewModelMock
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

function buildWorkspaceFromProfile(profile: BackendExamProfile): PscppWorkspaceViewModel {
  return {
    ...pscppWorkspaceViewModelMock,
    connection: sourceConnection(
      "backend",
      "Dados reais disponíveis",
      "Perfil PSCPP confirmado. O ciclo sugerido e a orientação de questões seguem como guia de consulta.",
      "connected"
    ),
    profileTitle: profile.profile_name || pscppWorkspaceViewModelMock.profileTitle,
    profileDescription: profile.description || pscppWorkspaceViewModelMock.profileDescription,
    examProfileId: profile.profile_id || pscppWorkspaceViewModelMock.examProfileId,
    questionStyleProfileId:
      profile.question_style_profile?.profile_id ||
      pscppWorkspaceViewModelMock.questionStyleProfileId
  };
}

function buildCycleView(source: ApiSource): PscppCycleViewModel {
  if (source === "backend") {
    return {
      ...pscppCycleViewModelMock,
      connection: sourceConnection(
        "backend",
        "Dados reais disponíveis",
        "A leitura do perfil foi confirmada, mas o ciclo continua como guia flexível, sem agenda automática ou alteração de progresso.",
        "connected"
      )
    };
  }

  if (source === "offline") {
    return {
      ...pscppCycleViewModelMock,
      connection: sourceConnection(
        "offline",
        "Dados reais não carregados agora",
        "Mostrando referência local enquanto os dados reais não estão disponíveis.",
        "offline"
      )
    };
  }

  if (source === "unsupported") {
    return {
      ...pscppCycleViewModelMock,
      connection: sourceConnection(
        "unsupported",
        "Demonstração",
        "Não há leitura dedicada para o ciclo PSCPP nesta etapa; o guia continua em orientação de demonstração.",
        "unsupported"
      )
    };
  }

  return {
    ...pscppCycleViewModelMock,
    connection: cloneConnection(pscppCycleViewModelMock.connection)
  };
}

function buildQuestionsView(source: ApiSource): PscppQuestionsViewModel {
  if (source === "backend") {
    return {
      ...pscppQuestionsViewModelMock,
      connection: sourceConnection(
        "backend",
        "Dados reais disponíveis",
        "O perfil PSCPP foi confirmado. Esta tela continua como guia de questões candidatas e revisão.",
        "connected"
      )
    };
  }

  if (source === "offline") {
    return {
      ...pscppQuestionsViewModelMock,
      connection: sourceConnection(
        "offline",
        "Dados reais não carregados agora",
        "Mostrando referência local enquanto os dados reais não estão disponíveis.",
        "offline"
      )
    };
  }

  if (source === "unsupported") {
    return {
      ...pscppQuestionsViewModelMock,
      connection: sourceConnection(
        "unsupported",
        "Demonstração",
        "Não há leitura dedicada para orientação de questões PSCPP nesta etapa; a tela permanece em orientação de demonstração.",
        "unsupported"
      )
    };
  }

  return {
    ...pscppQuestionsViewModelMock,
    connection: cloneConnection(pscppQuestionsViewModelMock.connection)
  };
}

export function buildMockPscppWorkspaceViewModel(): PscppWorkspaceViewModel {
  return {
    ...pscppWorkspaceViewModelMock,
    connection: cloneConnection(pscppWorkspaceViewModelMock.connection)
  };
}

export function buildMockPscppCycleViewModel(): PscppCycleViewModel {
  return {
    ...pscppCycleViewModelMock,
    connection: cloneConnection(pscppCycleViewModelMock.connection)
  };
}

export function buildMockPscppQuestionsViewModel(): PscppQuestionsViewModel {
  return {
    ...pscppQuestionsViewModelMock,
    connection: cloneConnection(pscppQuestionsViewModelMock.connection)
  };
}

export async function loadPscppWorkspaceViewModel(): Promise<PscppWorkspaceViewModel> {
  const fallback = buildMockPscppWorkspaceViewModel();
  const result = await fetchPscppExamProfile();

  if (result.ok) {
    return buildWorkspaceFromProfile(result.data);
  }

  if (result.source === "offline") {
    return {
      ...fallback,
      connection: sourceConnection(
        "offline",
        "Dados reais não carregados agora",
        "Mostrando referência local enquanto os dados reais não estão disponíveis.",
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
        "O endpoint do perfil PSCPP não está disponível neste ambiente; usando orientação de demonstração.",
        "unsupported"
      )
    };
  }

  return fallback;
}

export async function loadPscppCycleViewModel(): Promise<PscppCycleViewModel> {
  const result = await fetchPscppExamProfile();
  if (result.ok) {
    return buildCycleView("backend");
  }
  if (result.source === "offline") {
    return buildCycleView("offline");
  }
  if (result.source === "unsupported") {
    return buildCycleView("unsupported");
  }
  return buildMockPscppCycleViewModel();
}

export async function loadPscppQuestionsViewModel(): Promise<PscppQuestionsViewModel> {
  const result = await fetchPscppExamProfile();
  if (result.ok) {
    return buildQuestionsView("backend");
  }
  if (result.source === "offline") {
    return buildQuestionsView("offline");
  }
  if (result.source === "unsupported") {
    return buildQuestionsView("unsupported");
  }
  return buildMockPscppQuestionsViewModel();
}
