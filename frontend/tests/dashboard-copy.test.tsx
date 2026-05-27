import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/adapters/session", () => ({
  buildDefaultSessionState: vi.fn(() => ({
    status: "unauthenticated",
    label: "Sessão necessária",
    description: "Entre para usar dados reais. Enquanto isso, o painel usa dados de demonstração.",
    source: "backend"
  })),
  loadSessionState: vi.fn(async () => ({
    status: "unauthenticated",
    label: "Sessão necessária",
    description: "Entre para usar dados reais. Enquanto isso, o painel usa dados de demonstração.",
    source: "backend"
  }))
}));

vi.mock("@/lib/adapters/dashboard", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/dashboard")>(
    "@/lib/adapters/dashboard"
  );

  return {
    ...actual,
    loadDashboardViewModel: vi.fn(async () => actual.buildMockDashboardViewModel())
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
  it("keeps dashboard sections in product language and avoids forbidden CTAs", async () => {
    render(<DashboardReadOnlyClient />);

    expect(await screen.findByText("Estudo de hoje")).toBeInTheDocument();
    expect(screen.getByText(/o que já está preparado/i)).toBeInTheDocument();
    expect(screen.getByText(/uso controlado/i)).toBeInTheDocument();
    expect(screen.getAllByText("Questões candidatas").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Simulado em preparação").length).toBeGreaterThan(0);
    expect(screen.getByText("Consulta local")).toBeInTheDocument();
    expect(screen.getAllByText("Requer sessão").length).toBeGreaterThan(0);
    expect(screen.queryByText(/dados reais da sessão/i)).not.toBeInTheDocument();

    expect(screen.queryByText(/ledger/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/guardrail/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/propagation/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/artifact/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/runtime chain/i)).not.toBeInTheDocument();

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
