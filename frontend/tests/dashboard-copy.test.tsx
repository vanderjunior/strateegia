import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  session: {
    status: "unauthenticated",
    label: "Sessão necessária",
    description: "Entre para usar dados reais. Enquanto isso, o painel evita dados personalizados.",
    source: "backend"
  } as Record<string, unknown>,
  dashboardOverrides: {} as Record<string, unknown>,
  readiness: {
    connection: {
      state: "auth_required",
      source: "backend",
      title: "Entre para carregar seus dados",
      detail: "A orientação real depende de uma sessão ativa."
    },
    isAuthenticated: false,
    hasRealMaterials: false,
    hasRealEditalMaterial: false,
    hasRealStudyMaterial: false,
    hasAnalyzedEdital: false,
    editalAnalysisState: "analysis_unavailable",
    editalAnalysisLabel: "Análise indisponível",
    editalAnalysisDescription: "Não foi possível confirmar o estado da análise agora.",
    canShowConcreteStudyPlan: false,
    shouldShowEditalUploadCTA: true,
    shouldShowStudyMaterialCTA: false,
    materialsCount: 0,
    editalMaterialsCount: 0,
    studyMaterialsCount: 0,
    materialTypeCounts: {
      edital: 0,
      study_material: 0,
      previous_exam: 0,
      bibliography: 0,
      note: 0,
      other: 0,
      unknown: 0
    }
  } as Record<string, unknown>
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

vi.mock("@/lib/adapters/real-user-state", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/real-user-state")>(
    "@/lib/adapters/real-user-state"
  );

  return {
    ...actual,
    buildDefaultRealUserStudyReadiness: vi.fn(() => mocks.readiness),
    loadRealUserStudyReadiness: vi.fn(async () => mocks.readiness)
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
    mocks.readiness = {
      connection: {
        state: "auth_required",
        source: "backend",
        title: "Entre para carregar seus dados",
        detail: "A orientação real depende de uma sessão ativa."
      },
      isAuthenticated: false,
      hasRealMaterials: false,
      hasRealEditalMaterial: false,
      hasRealStudyMaterial: false,
      hasAnalyzedEdital: false,
      editalAnalysisState: "analysis_unavailable",
      editalAnalysisLabel: "Análise indisponível",
      editalAnalysisDescription: "Não foi possível confirmar o estado da análise agora.",
      canShowConcreteStudyPlan: false,
      shouldShowEditalUploadCTA: true,
      shouldShowStudyMaterialCTA: false,
      materialsCount: 0,
      editalMaterialsCount: 0,
      studyMaterialsCount: 0,
      materialTypeCounts: {
        edital: 0,
        study_material: 0,
        previous_exam: 0,
        bibliography: 0,
        note: 0,
        other: 0,
        unknown: 0
      }
    };
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
    mocks.readiness = {
      connection: {
        state: "connected",
        source: "backend",
        title: "Dados reais da sessão",
        detail: "Estado real calculado."
      },
      isAuthenticated: true,
      hasRealMaterials: false,
      hasRealEditalMaterial: false,
      hasRealStudyMaterial: false,
      hasAnalyzedEdital: false,
      editalAnalysisState: "no_edital_uploaded",
      editalAnalysisLabel: "Nenhum edital enviado",
      editalAnalysisDescription: "Envie um edital para orientar seu caminho de estudo.",
      canShowConcreteStudyPlan: false,
      shouldShowEditalUploadCTA: true,
      shouldShowStudyMaterialCTA: false,
      materialsCount: 0,
      editalMaterialsCount: 0,
      studyMaterialsCount: 0,
      materialTypeCounts: {
        edital: 0,
        study_material: 0,
        previous_exam: 0,
        bibliography: 0,
        note: 0,
        other: 0,
        unknown: 0
      }
    };

    render(<DashboardReadOnlyClient />);

    expect((await screen.findAllByText("Envie um edital para orientar seu caminho de estudo.")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Estudo de hoje")).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Enviar edital" })[0]).toHaveAttribute("href", "/materials/upload");
    expect(screen.getAllByRole("link", { name: "Ver materiais" })[0]).toHaveAttribute("href", "/materials");
    expect(screen.getByText("Materiais enviados por tipo")).toBeInTheDocument();
    expect(screen.queryByText(/capabilities/i)).not.toBeInTheDocument();
    expect(screen.queryByText("O que já está preparado")).not.toBeInTheDocument();
  });

  it("shows uploaded edital state without concrete study session before analysis", async () => {
    mocks.session = {
      status: "authenticated",
      label: "Sessão ativa",
      description: "Sessão ativa.",
      source: "backend",
      userLabel: "Usuário interno"
    };
    mocks.readiness = {
      connection: {
        state: "connected",
        source: "backend",
        title: "Dados reais da sessão",
        detail: "Estado real calculado."
      },
      isAuthenticated: true,
      hasRealMaterials: true,
      hasRealEditalMaterial: true,
      hasRealStudyMaterial: true,
      hasAnalyzedEdital: false,
      editalAnalysisState: "edital_uploaded_not_analyzed",
      editalAnalysisLabel: "Edital enviado",
      editalAnalysisDescription: "Edital recebido. A análise ainda não foi executada nesta versão.",
      canShowConcreteStudyPlan: false,
      shouldShowEditalUploadCTA: false,
      shouldShowStudyMaterialCTA: true,
      materialsCount: 4,
      editalMaterialsCount: 1,
      studyMaterialsCount: 2,
      materialTypeCounts: {
        edital: 1,
        study_material: 2,
        previous_exam: 0,
        bibliography: 0,
        note: 0,
        other: 1,
        unknown: 0
      }
    };

    render(<DashboardReadOnlyClient />);

    expect(
      (await screen.findAllByText("Edital recebido. A análise ainda não foi executada nesta versão.")).length
    ).toBeGreaterThan(0);
    expect(screen.queryByText("Estudo de hoje")).not.toBeInTheDocument();
    expect(screen.getByText(/Materiais de estudo enviados: 2/i)).toBeInTheDocument();
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
