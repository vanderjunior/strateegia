import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  session: {
    status: "unauthenticated",
    label: "Sessão necessária",
    description: "Entre para usar dados reais. Enquanto isso, o painel evita dados personalizados.",
    source: "backend"
  } as Record<string, unknown>,
  dashboardOverrides: {} as Record<string, unknown>
}));

vi.mock("@/lib/adapters/session", () => ({
  SESSION_STATE_CHANGED_EVENT: "mentorium:session-state-changed",
  buildDefaultSessionState: vi.fn(() => mocks.session),
  loadSessionState: vi.fn(async () => mocks.session),
  notifySessionStateChanged: vi.fn()
}));

vi.mock("@/lib/adapters/dashboard", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/dashboard")>(
    "@/lib/adapters/dashboard"
  );

  return {
    ...actual,
    loadDashboardViewModel: vi.fn(async () => actual.buildMockDashboardViewModel(mocks.dashboardOverrides))
  };
});

vi.mock("@/lib/adapters/study-sessions", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/study-sessions")>(
    "@/lib/adapters/study-sessions"
  );

  return {
    ...actual,
    loadStudySessionWorkspaceViewModel: vi.fn(async () => actual.buildMockStudySessionWorkspaceViewModel())
  };
});

import { DashboardReadOnlyClient } from "@/components/dashboard/DashboardReadOnlyClient";

describe("dashboard product language", () => {
  beforeEach(() => {
    mocks.session = {
      status: "unauthenticated",
      label: "Sessão necessária",
      description: "Entre para usar dados reais. Enquanto isso, o painel evita dados personalizados.",
      source: "backend"
    };
    mocks.dashboardOverrides = {};
  });

  it("keeps unauthenticated dashboard simple and avoids personalized study content", async () => {
    render(<DashboardReadOnlyClient />);

    expect(await screen.findByText("Entre para ver seus materiais, edital e caminho de estudo.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Entrar" })[0]).toHaveAttribute("href", "/login");
    expect(screen.getByRole("link", { name: "Conhecer o fluxo" })).toHaveAttribute("href", "/onboarding");
    expect(screen.queryByText("Estudo de hoje")).not.toBeInTheDocument();
    expect(screen.queryByText(/Questões candidatas/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Simulado em preparação/i)).not.toBeInTheDocument();

    expect(screen.queryByText(/Backend offline/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Não foi possível conectar ao backend/i)).not.toBeInTheDocument();
  });

  it("shows next-step guidance instead of a concrete study session when no real edital exists", async () => {
    mocks.session = {
      status: "authenticated",
      label: "Sessão ativa",
      description: "Sessão ativa.",
      source: "backend",
      userLabel: "Usuário interno"
    };
    mocks.dashboardOverrides = {
      usesRealUserData: true,
      hasRealEditalContext: false,
      connection: {
        state: "connected",
        source: "backend",
        title: "Dados reais disponíveis",
        detail: "Materiais reais carregados para esta sessão."
      }
    };

    render(<DashboardReadOnlyClient />);

    expect(await screen.findByText("Envie ou identifique um edital para montar o caminho de estudo.")).toBeInTheDocument();
    expect(screen.queryByText("Estudo de hoje")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Enviar material" })).toHaveAttribute("href", "/materials/upload");
    expect(screen.getByRole("link", { name: "Ver editais" })).toHaveAttribute("href", "/editais");
  });

  it("keeps dashboard free of mutation and pricing CTAs", async () => {
    render(<DashboardReadOnlyClient />);

    expect(await screen.findByText("Entre para ver seus materiais, edital e caminho de estudo.")).toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
    expect(screen.queryByText("Agendar")).not.toBeInTheDocument();
    expect(screen.queryByText("Começar sessão")).not.toBeInTheDocument();
    expect(screen.queryByText("Concluir sessão")).not.toBeInTheDocument();
    expect(screen.queryByText("Comprar")).not.toBeInTheDocument();
    expect(screen.queryByText("Assinar plano")).not.toBeInTheDocument();
  });
});
