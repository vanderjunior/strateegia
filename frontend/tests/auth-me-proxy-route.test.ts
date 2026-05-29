import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/api/auth/me/route";
import { POST as LOGIN } from "@/app/api/auth/login/route";
import { POST as LOGOUT } from "@/app/api/auth/logout/route";

describe("auth me same-origin proxy route", () => {
  const originalBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const originalInternalUrl = process.env.BACKEND_INTERNAL_URL;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000";
    process.env.BACKEND_INTERNAL_URL = "http://backend:8000";
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
    process.env.BACKEND_INTERNAL_URL = originalInternalUrl;
    vi.unstubAllGlobals();
  });

  it("targets the internal backend URL and forwards cookies server-side", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify({ authenticated: true, user_id: "user-1" }), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/auth/me", {
        headers: { cookie: "studyflow_session=server-only" }
      })
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/auth/me",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("returns 503 when neither backend URL is configured", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await GET(new Request("http://localhost/api/auth/me"));

    expect(response.status).toBe(503);
  });

  it("login proxy forwards JSON body and Set-Cookie without exposing credentials", async () => {
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
        {
          status: 200,
          headers: {
            "content-type": "application/json",
            "set-cookie": "studyflow_session=server-only; HttpOnly; SameSite=Lax"
          }
        }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await LOGIN(
      new Request("http://localhost/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ username: "mentorium", password: "senha-segura-123" })
      })
    );
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toContain("studyflow_session");
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ username: "mentorium", password: "senha-segura-123" }),
        cache: "no-store"
      })
    );
    expect(payload.authenticated).toBe(true);
    expect(dumped).not.toContain("senha-segura-123");
    expect(dumped).not.toContain("studyflow_session=server-only");
    expect(dumped).not.toContain("password_hash");
  });

  it.each([401, 422])("login proxy preserves backend status %i", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Backend auth response." }), {
          status,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const response = await LOGIN(
      new Request("http://localhost/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ username: "mentorium", password: "wrong-password" })
      })
    );

    expect(response.status).toBe(status);
  });

  it("login proxy returns 503 when backend URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await LOGIN(
      new Request("http://localhost/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: "mentorium", password: "senha-segura-123" })
      })
    );

    expect(response.status).toBe(503);
  });

  it("logout proxy forwards cookies server-side and propagates clear-cookie", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(JSON.stringify({ authenticated: false, user: null }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "set-cookie": "studyflow_session=; Max-Age=0; HttpOnly; SameSite=Lax"
        }
      })
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await LOGOUT(
      new Request("http://localhost/api/auth/logout", {
        method: "POST",
        headers: { cookie: "studyflow_session=server-only" }
      })
    );
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toContain("Max-Age=0");
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/auth/logout",
      expect.objectContaining({
        method: "POST",
        headers: { cookie: "studyflow_session=server-only", accept: "application/json" },
        cache: "no-store"
      })
    );
    expect(payload).toEqual({ authenticated: false, user: null });
    expect(dumped).not.toContain("studyflow_session=server-only");
    expect(dumped).not.toContain("password_hash");
  });

  it("logout proxy returns 503 when backend URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    const response = await LOGOUT(
      new Request("http://localhost/api/auth/logout", {
        method: "POST"
      })
    );

    expect(response.status).toBe(503);
  });

  it("login and logout proxies map backend connectivity failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    const loginResponse = await LOGIN(
      new Request("http://localhost/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: "mentorium", password: "senha-segura-123" })
      })
    );
    const logoutResponse = await LOGOUT(
      new Request("http://localhost/api/auth/logout", {
        method: "POST"
      })
    );

    expect(loginResponse.status).toBe(502);
    expect(logoutResponse.status).toBe(502);
  });
});
