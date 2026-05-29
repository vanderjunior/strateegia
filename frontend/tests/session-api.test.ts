import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { fetchCurrentSession, loginWithPassword, logoutCurrentSession } from "@/lib/api/auth";
import { getApiConfig } from "@/lib/api/config";

describe("session API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("returns mock mode without calling fetch", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchCurrentSession();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("mock_mode");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("returns missing_base_url when session base URL is absent", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: null,
      forceMock: false
    });

    const result = await fetchCurrentSession();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("missing_base_url");
    expect(result.error.message).toBe("Sessão real não configurada neste ambiente.");
  });

  it.each([
    [502, "backend_offline", "Não foi possível conectar ao backend."],
    [503, "missing_base_url", "Sessão real não configurada neste ambiente."],
    [401, "unauthorized", "Sessão necessária."],
    [403, "unauthorized", "Sessão necessária."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchCurrentSession();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("returns the bounded backend session payload on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            authenticated: true,
            user: {
              user_id: "user-1",
              username: "mentorium",
              display_name: "Mentorium Demo",
              email: "demo@example.com"
            }
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchCurrentSession();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data).toEqual({
      authenticated: true,
      user: {
        user_id: "user-1",
        username: "mentorium",
        display_name: "Mentorium Demo",
        email: "demo@example.com"
      }
    });
  });

  it("logs in with password without storing credentials", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          authenticated: true,
          user: {
            user_id: "user-1",
            username: "mentorium",
            display_name: "Mentorium Demo"
          }
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const result = await loginWithPassword({
      username: "mentorium",
      password: "senha-segura-123"
    });

    expect(result.ok).toBe(true);
    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ username: "mentorium", password: "senha-segura-123" })
      })
    );
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(JSON.stringify(result.data)).not.toContain("senha-segura-123");
  });

  it.each([
    [401, "invalid_credentials", "Credenciais inválidas."],
    [422, "validation_failed", "Preencha usuário e senha para entrar."],
    [502, "backend_offline", "Não foi possível conectar ao backend."],
    [503, "missing_base_url", "Sessão não configurada neste ambiente."]
  ])("maps login HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await loginWithPassword({ username: "mentorium", password: "wrong-password" });

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("logs out the current session", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ authenticated: false, user: null }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const result = await logoutCurrentSession();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data).toEqual({ authenticated: false, user: null });
  });
});
