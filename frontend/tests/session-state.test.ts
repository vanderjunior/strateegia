import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

vi.mock("@/lib/api/auth", () => ({
  fetchCurrentSession: vi.fn()
}));

import { getApiConfig } from "@/lib/api/config";
import { fetchCurrentSession } from "@/lib/api/auth";
import {
  __resetSessionStateCacheForTests,
  buildDefaultSessionState,
  loadSessionState
} from "@/lib/adapters/session";

describe("session state adapter", () => {
  beforeEach(() => {
    __resetSessionStateCacheForTests();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
    vi.mocked(fetchCurrentSession).mockReset();
  });

  it("maps authenticated responses to Sessão ativa", async () => {
    vi.mocked(fetchCurrentSession).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        authenticated: true,
        user: {
          user_id: "user-1",
          display_name: "Cap. Silva",
          username: "cap.silva",
          email: "cap@example.com"
        }
      }
    });

    const result = await loadSessionState({ refresh: true });

    expect(result.status).toBe("authenticated");
    expect(result.label).toBe("Sessão ativa");
    expect(result.userId).toBe("user-1");
    expect(result.userLabel).toBe("Cap. Silva");
  });

  it("maps unauthenticated backend responses to Entrar para continuar", async () => {
    vi.mocked(fetchCurrentSession).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        authenticated: false,
        user: null
      }
    });

    const result = await loadSessionState({ refresh: true });

    expect(result.status).toBe("unauthenticated");
    expect(result.label).toBe("Entrar para continuar");
    expect(result.description).toContain("materiais");
  });

  it("maps network failures to Dados indisponíveis", async () => {
    vi.mocked(fetchCurrentSession).mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: {
        code: "backend_offline",
        message: "Não foi possível carregar o acesso agora."
      }
    });

    const result = await loadSessionState({ refresh: true });

    expect(result.status).toBe("backend_offline");
    expect(result.label).toBe("Dados indisponíveis");
  });

  it("maps mock mode from config without exposing sensitive auth internals", () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });

    const result = buildDefaultSessionState();
    const serialized = JSON.stringify(result);

    expect(result.status).toBe("mock_mode");
    expect(result.label).toBe("Modo demonstração");
    expect(serialized).not.toContain("token");
    expect(serialized).not.toContain("cookie");
    expect(serialized).not.toContain("password_hash");
  });
});
