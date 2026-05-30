import type { ProtectedReadPolicy, SessionState } from "@/lib/api/types";

export function resolveProtectedReadPolicy(sessionState: SessionState): ProtectedReadPolicy {
  switch (sessionState.status) {
    case "authenticated":
      return {
        mode: "real_authenticated",
        label: "Dados reais da sessão",
        description:
          "Esta área pode consultar dados reais da sua sessão quando a leitura protegida estiver disponível, sem alterar seu progresso automaticamente.",
        badgeTone: "positive",
        canUseRealData: true,
        shouldShowDemoFallback: true,
        shouldShowSessionRequired: false,
        shouldAttemptProtectedRead: true,
        recommendedUserCopy:
          "Dados reais da sessão podem aparecer aqui quando esta área estiver ligada à leitura protegida. A demonstração continua disponível como apoio."
      };
    case "unauthenticated":
      return {
        mode: "requires_session",
        label: "Requer sessão",
        description:
          "Entre para usar dados reais desta área. Enquanto isso, o app pode mostrar dados de demonstração claramente identificados.",
        badgeTone: "warning",
        canUseRealData: false,
        shouldShowDemoFallback: true,
        shouldShowSessionRequired: true,
        shouldAttemptProtectedRead: false,
        recommendedUserCopy:
          "Entre para usar dados reais. Enquanto isso, os dados de demonstração seguem visíveis como apoio."
      };
    case "mock_mode":
      return {
        mode: "demo",
        label: "Modo demonstração",
        description:
          "Este ambiente usa apenas dados de demonstração auditados e não tenta consultar leituras protegidas do backend.",
        badgeTone: "neutral",
        canUseRealData: false,
        shouldShowDemoFallback: true,
        shouldShowSessionRequired: false,
        shouldAttemptProtectedRead: false,
        recommendedUserCopy:
          "A área permanece em demonstração local. Nenhum dado real da sessão foi carregado."
      };
    case "backend_offline":
      return {
        mode: "backend_offline",
        label: "Dados indisponíveis",
        description:
          "Não foi possível carregar dados reais agora. A demonstração continua disponível e isso não indica perda de dados.",
        badgeTone: "warning",
        canUseRealData: false,
        shouldShowDemoFallback: true,
        shouldShowSessionRequired: false,
        shouldAttemptProtectedRead: false,
        recommendedUserCopy:
          "Dados reais não carregados agora. Use os dados de demonstração como apoio até a conexão voltar."
      };
    default:
      return {
        mode: "unsupported",
        label: "Demonstração",
        description:
          "A área segue acessível com dados de demonstração.",
        badgeTone: "muted",
        canUseRealData: false,
        shouldShowDemoFallback: true,
        shouldShowSessionRequired: false,
        shouldAttemptProtectedRead: false,
        recommendedUserCopy:
          "A demonstração continua disponível enquanto a leitura protegida desta área ainda não está configurada."
      };
  }
}

export function protectedReadBadgeClass(tone: ProtectedReadPolicy["badgeTone"]): string {
  switch (tone) {
    case "positive":
      return "border-emerald-400/30 bg-emerald-400/12 text-emerald-100";
    case "warning":
      return "border-amber-400/30 bg-amber-400/12 text-amber-100";
    case "muted":
      return "border-rose-400/30 bg-rose-400/12 text-rose-100";
    default:
      return "border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.10)] text-silver";
  }
}
