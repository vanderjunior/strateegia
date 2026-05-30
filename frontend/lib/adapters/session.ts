import { fetchCurrentSession } from "@/lib/api/auth";
import { getApiConfig } from "@/lib/api/config";
import type { SessionState } from "@/lib/api/types";

export const SESSION_STATE_CHANGED_EVENT = "mentorium:session-state-changed";

let sessionStatePromise: Promise<SessionState> | null = null;

function userLabelForSession(user: {
  display_name?: string | null;
  username?: string | null;
  email?: string | null;
} | null): string | undefined {
  if (!user) {
    return undefined;
  }

  return user.display_name ?? user.username ?? user.email ?? undefined;
}

export function buildStaticSessionState(): SessionState | null {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return {
      status: "mock_mode",
      label: "Modo demonstração",
      description: "Este ambiente usa dados de demonstração e não consulta a sessão real.",
      source: "mock"
    };
  }

  if (!baseUrl) {
    return {
      status: "unsupported",
      label: "Sessão não configurada",
      description: "Entre para usar dados reais quando a sessão estiver disponível.",
      source: "unsupported"
    };
  }

  return null;
}

export function buildDefaultSessionState(): SessionState {
  return (
    buildStaticSessionState() ?? {
      status: "unauthenticated",
      label: "Entrar para continuar",
      description: "Entre para acessar seus materiais.",
      source: "backend"
    }
  );
}

export async function loadSessionState(options: { refresh?: boolean } = {}): Promise<SessionState> {
  if (options.refresh || sessionStatePromise === null) {
    sessionStatePromise = loadSessionStateUncached();
  }

  return sessionStatePromise;
}

async function loadSessionStateUncached(): Promise<SessionState> {
  const staticState = buildStaticSessionState();
  if (staticState) {
    return staticState;
  }

  const result = await fetchCurrentSession();

  if (!result.ok) {
    if (result.error.code === "mock_mode") {
      return {
        status: "mock_mode",
        label: "Modo demonstração",
        description: "Demonstração disponível para conhecer o fluxo.",
        source: "mock"
      };
    }

    if (result.error.code === "missing_base_url") {
      return {
        status: "unsupported",
        label: "Sessão não configurada",
        description: "Entre para usar dados reais quando a sessão estiver disponível.",
        source: "unsupported"
      };
    }

    if (result.error.code === "backend_offline" || result.error.code === "network_error" || result.error.code === "timeout") {
      return {
        status: "backend_offline",
        label: "Dados indisponíveis",
        description: "Não foi possível confirmar a sessão agora.",
        source: "offline"
      };
    }

    return {
      status: "unauthenticated",
      label: "Entrar para continuar",
      description: "Entre para acessar seus materiais.",
      source: "backend"
    };
  }

  if (!result.data.authenticated || !result.data.user) {
    return {
    status: "unauthenticated",
    label: "Entrar para continuar",
    description: "Entre para acessar seus materiais.",
      source: "backend"
    };
  }

  return {
    status: "authenticated",
    label: "Sessão ativa",
    description: "Você está conectado.",
    source: "backend",
    userId: result.data.user.user_id ?? undefined,
    userLabel: userLabelForSession(result.data.user)
  };
}

export function __resetSessionStateCacheForTests() {
  sessionStatePromise = null;
}

export function notifySessionStateChanged() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(SESSION_STATE_CHANGED_EVENT));
  }
}
