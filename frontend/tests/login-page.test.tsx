import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const routerMocks = vi.hoisted(() => ({
  push: vi.fn(),
  refresh: vi.fn()
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerMocks.push,
    refresh: routerMocks.refresh
  })
}));

vi.mock("@/lib/api/auth", () => ({
  loginWithPassword: vi.fn()
}));

vi.mock("@/lib/adapters/session", () => ({
  loadSessionState: vi.fn(),
  notifySessionStateChanged: vi.fn()
}));

import LoginPage from "@/app/(app)/login/page";
import { loginWithPassword } from "@/lib/api/auth";
import { loadSessionState, notifySessionStateChanged } from "@/lib/adapters/session";

describe("login page", () => {
  beforeEach(() => {
    routerMocks.push.mockClear();
    routerMocks.refresh.mockClear();
    vi.mocked(loadSessionState).mockResolvedValue({
      status: "authenticated",
      label: "Sessão ativa",
      description: "Dados reais podem ser consultados nas áreas protegidas sem alterar seu progresso automaticamente.",
      source: "backend",
      userId: "user-1",
      userLabel: "Mentorium Demo"
    });
  });

  it("renders minimal internal staging login without signup UI or auth internals", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.getByLabelText("Usuário")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.getAllByText("Voltar ao painel").length).toBeGreaterThan(0);
    expect(screen.getByText(/Sessões são locais neste ambiente/i)).toBeInTheDocument();
    expect(screen.queryByText(/criar conta/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cadastro/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/token/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cookie/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/password hash/i)).not.toBeInTheDocument();
  });

  it("shows invalid credentials copy", async () => {
    vi.mocked(loginWithPassword).mockResolvedValue({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "invalid_credentials",
        message: "Credenciais inválidas."
      }
    });

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Usuário"), {
      target: { value: "mentorium" }
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senha-incorreta" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByText("Credenciais inválidas.")).toBeInTheDocument();
  });

  it("refreshes session after successful login", async () => {
    vi.mocked(loginWithPassword).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        authenticated: true,
        user: {
          user_id: "user-1",
          username: "mentorium",
          display_name: "Mentorium Demo"
        }
      }
    });

    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Usuário"), {
      target: { value: "mentorium" }
    });
    fireEvent.change(screen.getByLabelText("Senha"), {
      target: { value: "senha-segura-123" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => {
      expect(loadSessionState).toHaveBeenCalledWith({ refresh: true });
    });
    expect(notifySessionStateChanged).toHaveBeenCalled();
    expect(routerMocks.refresh).toHaveBeenCalled();
    expect(routerMocks.push).toHaveBeenCalledWith("/dashboard");
    expect(await screen.findByText("Sessão ativa. Redirecionando para o painel.")).toBeInTheDocument();
    expect(screen.queryByText("senha-segura-123")).not.toBeInTheDocument();
  });
});
