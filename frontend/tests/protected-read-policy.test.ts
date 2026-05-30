import { describe, expect, it } from "vitest";

import { resolveProtectedReadPolicy } from "@/lib/auth/protected-read-policy";
import type { SessionState } from "@/lib/api/types";

function makeSessionState(overrides: Partial<SessionState>): SessionState {
  return {
    status: "unauthenticated",
    label: "Entrar para continuar",
    description: "Entre para acessar seus materiais.",
    source: "backend",
    ...overrides
  };
}

describe("protected read UX policy", () => {
  it("maps authenticated sessions to real_authenticated", () => {
    const policy = resolveProtectedReadPolicy(
      makeSessionState({
        status: "authenticated",
        label: "Sessão ativa",
        description: "Dados reais podem ser consultados.",
        userId: "user-1",
        userLabel: "Mentorium Demo"
      })
    );

    expect(policy.mode).toBe("real_authenticated");
    expect(policy.label).toBe("Dados reais");
    expect(policy.canUseRealData).toBe(true);
    expect(policy.shouldAttemptProtectedRead).toBe(true);
  });

  it("maps unauthenticated sessions to requires_session without claiming real user data", () => {
    const policy = resolveProtectedReadPolicy(makeSessionState({}));

    expect(policy.mode).toBe("requires_session");
    expect(policy.label).toBe("Requer sessão");
    expect(policy.canUseRealData).toBe(false);
    expect(policy.shouldShowSessionRequired).toBe(true);
    expect(policy.recommendedUserCopy).not.toContain("dados reais da sessão já carregados");
  });

  it("maps mock mode to demo", () => {
    const policy = resolveProtectedReadPolicy(
      makeSessionState({
        status: "mock_mode",
        label: "Modo demonstração",
        description: "Este ambiente usa dados de demonstração.",
        source: "mock"
      })
    );

    expect(policy.mode).toBe("demo");
    expect(policy.shouldShowDemoFallback).toBe(true);
    expect(policy.shouldAttemptProtectedRead).toBe(false);
  });

  it("maps backend_offline to product-safe unavailable copy", () => {
    const policy = resolveProtectedReadPolicy(
      makeSessionState({
        status: "backend_offline",
        label: "Dados indisponíveis",
        description: "Não foi possível confirmar a sessão agora.",
        source: "offline"
      })
    );

    expect(policy.mode).toBe("backend_offline");
    expect(policy.label).toBe("Dados indisponíveis");
    expect(policy.shouldShowDemoFallback).toBe(true);
  });

  it("maps unsupported to unsupported", () => {
    const policy = resolveProtectedReadPolicy(
      makeSessionState({
        status: "unsupported",
        label: "Sessão não configurada",
        description: "Sessão real não configurada neste ambiente.",
        source: "unsupported"
      })
    );

    expect(policy.mode).toBe("unsupported");
    expect(policy.label).toBe("Demonstração");
    expect(policy.shouldAttemptProtectedRead).toBe(false);
  });

  it("never exposes token, cookie, or password hash in the serialized policy", () => {
    const payload = JSON.stringify(
      resolveProtectedReadPolicy(
        makeSessionState({
          status: "authenticated",
          label: "Sessão ativa",
          description: "Dados reais podem ser consultados."
        })
      )
    );

    expect(payload).not.toContain("token");
    expect(payload).not.toContain("cookie");
    expect(payload).not.toContain("password_hash");
  });
});
