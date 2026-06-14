import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const pathnameMock = vi.hoisted(() => ({
  value: "/dashboard"
}));

vi.mock("@/lib/adapters/session", () => ({
  SESSION_STATE_CHANGED_EVENT: "mentorium:session-state-changed",
  buildDefaultSessionState: vi.fn(),
  loadSessionState: vi.fn(),
  notifySessionStateChanged: vi.fn()
}));

vi.mock("@/lib/api/auth", () => ({
  logoutCurrentSession: vi.fn()
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => pathnameMock.value)
}));

import { AppShell } from "@/components/layout/AppShell";
import { SessionStatusNotice } from "@/components/layout/SessionStatusNotice";
import { buildDefaultSessionState, loadSessionState } from "@/lib/adapters/session";
import { logoutCurrentSession } from "@/lib/api/auth";

describe("session status notice", () => {
  beforeEach(() => {
    pathnameMock.value = "/dashboard";
    vi.mocked(buildDefaultSessionState).mockReturnValue({
      status: "unauthenticated",
      label: "Entrar para continuar",
      description: "Entre para acessar seus materiais.",
      source: "backend"
    });
    vi.mocked(loadSessionState).mockResolvedValue({
      status: "authenticated",
      label: "Sessão ativa",
      description: "Você está conectado.",
      source: "backend",
      userId: "user-1",
      userLabel: "Mentorium Demo"
    });
  });

  it("renders product-safe session labels in the AppShell surface", async () => {
    render(<SessionStatusNotice />);

    expect(await screen.findByText("Sessão ativa")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sair" })).toBeInTheDocument();
    expect(screen.getAllByText(/Mentorium Demo/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/token/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cookie/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/password hash/i)).not.toBeInTheDocument();
  });

  it("renders the dashboard guidance copy without exposing auth internals", async () => {
    vi.mocked(loadSessionState).mockResolvedValue({
      status: "mock_mode",
      label: "Modo demonstração",
      description: "Conheça o fluxo antes de entrar.",
      source: "mock"
    });

    render(<SessionStatusNotice variant="dashboard" />);

    expect(await screen.findByText("Modo demonstração")).toBeInTheDocument();
    expect(screen.getByText(/Conheça o fluxo/i)).toBeInTheDocument();
    expect(screen.queryByText(/session id/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cookie/i)).not.toBeInTheDocument();
  });

  it("renders an Entrar link when unauthenticated", async () => {
    vi.mocked(loadSessionState).mockResolvedValue({
      status: "unauthenticated",
      label: "Entrar para continuar",
      description: "Entre para acessar seus materiais.",
      source: "backend"
    });

    render(<SessionStatusNotice />);

    expect(await screen.findByText("Entrar para continuar")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/login");
    expect(screen.queryByRole("button", { name: "Sair" })).not.toBeInTheDocument();
  });

  it("refreshes notice when the session changed event fires", async () => {
    vi.mocked(loadSessionState)
      .mockResolvedValueOnce({
        status: "unauthenticated",
        label: "Entrar para continuar",
        description: "Entre para acessar seus materiais.",
        source: "backend"
      })
      .mockResolvedValueOnce({
        status: "authenticated",
        label: "Sessão ativa",
        description: "Você está conectado.",
        source: "backend",
        userId: "user-1",
        userLabel: "Mentorium Demo"
      });

    render(<SessionStatusNotice />);

    expect(await screen.findByRole("link", { name: "Entrar" })).toBeInTheDocument();

    window.dispatchEvent(new Event("mentorium:session-state-changed"));

    expect(await screen.findByRole("button", { name: "Sair" })).toBeInTheDocument();
    expect(screen.getAllByText(/Mentorium Demo/i).length).toBeGreaterThan(0);
    expect(screen.queryByRole("link", { name: "Entrar" })).not.toBeInTheDocument();
  });

  it("returns to Entrar after logout", async () => {
    vi.mocked(logoutCurrentSession).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        authenticated: false,
        user: null
      }
    });
    vi.mocked(loadSessionState)
      .mockResolvedValueOnce({
        status: "authenticated",
        label: "Sessão ativa",
        description: "Você está conectado.",
        source: "backend",
        userId: "user-1",
        userLabel: "Mentorium Demo"
      })
      .mockResolvedValue({
        status: "unauthenticated",
        label: "Entrar para continuar",
        description: "Entre para acessar seus materiais.",
        source: "backend"
      });

    render(<SessionStatusNotice />);

    const logoutButton = await screen.findByRole("button", { name: "Sair" });
    fireEvent.click(logoutButton);

    await waitFor(() => {
      expect(logoutCurrentSession).toHaveBeenCalled();
    });
    expect(await screen.findByRole("link", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sair" })).not.toBeInTheDocument();
  });

  it("marks gated and future areas in the left navigation", async () => {
    pathnameMock.value = "/pscpp/ciclo";

    render(
      <AppShell>
        <div>Conteúdo</div>
      </AppShell>
    );

    expect(screen.getByRole("link", { name: /Dashboard/i })).toHaveAttribute("href", "/dashboard");
    expect(screen.getByRole("link", { name: /Ciclo Depois do edital/i })).toHaveAttribute(
      "href",
      "/pscpp/ciclo"
    );
    expect(screen.getByText("Questões").closest("[aria-disabled]")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getAllByText("Mais tarde").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText("Avaliações").closest("[aria-disabled]")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Execução").closest("[aria-disabled]")).toHaveAttribute("aria-disabled", "true");
    expect(screen.queryByText("Ainda não disponível")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Execução/i })).not.toBeInTheDocument();
  });
});
