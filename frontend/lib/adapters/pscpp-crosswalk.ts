import { fetchPscppExamProfile } from "@/lib/api/pscpp";
import type {
  ApiSource,
  BackendConnectionInfo,
  PscppCrosswalkViewModel
} from "@/lib/api/types";
import { pscppCrosswalkViewModelMock } from "@/lib/mock/mentorium-demo-data";

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

export function buildMockPscppCrosswalkViewModel(): PscppCrosswalkViewModel {
  return {
    ...pscppCrosswalkViewModelMock,
    connection: cloneConnection(pscppCrosswalkViewModelMock.connection)
  };
}

export async function loadPscppCrosswalkViewModel(): Promise<PscppCrosswalkViewModel> {
  const fallback = buildMockPscppCrosswalkViewModel();
  const result = await fetchPscppExamProfile();

  if (result.ok) {
    return {
      ...fallback,
      connection: sourceConnection(
        "backend",
        "Dados reais disponíveis",
        "Perfil PSCPP confirmado. O mapa continua como orientação de consulta.",
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
        "O perfil PSCPP não pôde ser confirmado neste ambiente; o mapa segue em orientação de demonstração.",
        "unsupported"
      )
    };
  }

  return fallback;
}
