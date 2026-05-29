import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/adapters/session", () => ({
  buildDefaultSessionState: vi.fn(),
  loadSessionState: vi.fn()
}));

vi.mock("@/lib/api/auth", () => ({
  logoutCurrentSession: vi.fn()
}));

import { SessionStatusNotice } from "@/components/layout/SessionStatusNotice";
import { buildDefaultSessionState, loadSessionState } from "@/lib/adapters/session";

describe("session status notice", () => {
  beforeEach(() => {
    vi.mocked(buildDefaultSessionState).mockReturnValue({
      status: "unauthenticated",
      label: "Sessão necessária",
      description: "Entre para usar dados reais. Enquanto isso, o painel usa dados de demonstração.",
      source: "backend"
    });
    vi.mocked(loadSessionState).mockResolvedValue({
      status: "authenticated",
      label: "Sessão ativa",
      description: "Dados reais podem ser consultados nas áreas protegidas sem alterar seu progresso automaticamente.",
      source: "backend",
      userId: "user-1",
      userLabel: "Mentorium Demo"
    });
  });

  it("renders product-safe session labels in the AppShell surface", async () => {
    render(<SessionStatusNotice />);

    expect(await screen.findByText("Sessão ativa")).toBeInTheDocument();
    expect(screen.getByText("Dados auditados")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sair" })).toBeInTheDocument();
    expect(screen.getByText(/Mentorium Demo/i)).toBeInTheDocument();
    expect(screen.queryByText(/token/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cookie/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/password hash/i)).not.toBeInTheDocument();
  });

  it("renders the dashboard guidance copy without exposing auth internals", async () => {
    vi.mocked(loadSessionState).mockResolvedValue({
      status: "mock_mode",
      label: "Modo demonstração",
      description: "Este ambiente usa dados de demonstração e não consulta a sessão real.",
      source: "mock"
    });

    render(<SessionStatusNotice variant="dashboard" />);

    expect(await screen.findByText("Modo demonstração")).toBeInTheDocument();
    expect(screen.getByText(/não consulta a sessão real/i)).toBeInTheDocument();
    expect(screen.queryByText(/session id/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cookie/i)).not.toBeInTheDocument();
  });

  it("renders an Entrar link when unauthenticated", async () => {
    vi.mocked(loadSessionState).mockResolvedValue({
      status: "unauthenticated",
      label: "Sessão necessária",
      description: "Entre para usar dados reais. Enquanto isso, o painel usa dados de demonstração.",
      source: "backend"
    });

    render(<SessionStatusNotice />);

    expect(await screen.findByText("Sessão necessária")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/login");
  });
});
