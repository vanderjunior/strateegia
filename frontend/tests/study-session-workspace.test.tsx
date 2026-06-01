import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const nextStudySessionMock = vi.hoisted(() => ({
  fetchNextStudySession: vi.fn()
}));

vi.mock("@/lib/api/study", () => ({
  fetchNextStudySession: nextStudySessionMock.fetchNextStudySession
}));

vi.mock("@/lib/adapters/study-sessions", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/study-sessions")>(
    "@/lib/adapters/study-sessions"
  );

  return {
    ...actual,
    loadStudySessionWorkspaceViewModel: vi.fn(async () => actual.buildMockStudySessionWorkspaceViewModel())
  };
});

vi.mock("@/lib/adapters/real-user-state", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/real-user-state")>(
    "@/lib/adapters/real-user-state"
  );

  return {
    ...actual,
    loadRealUserStudyReadiness: vi.fn(async () =>
      actual.buildDefaultRealUserStudyReadiness({
        connection: {
          state: "connected",
          source: "backend",
          title: "Dados reais",
          detail: "Dados reais disponíveis."
        },
        isAuthenticated: true,
        hasRealMaterials: true,
        hasRealStudyMaterial: true,
        hasAnalyzedEdital: false,
        canShowConcreteStudyPlan: false
      })
    )
  };
});

import { StudySessionWorkspaceClient } from "@/components/workspace/StudySessionWorkspaceClient";

describe("StudySessionWorkspaceClient next prepared material session", () => {
  beforeEach(() => {
    nextStudySessionMock.fetchNextStudySession.mockReset();
  });

  it("renders a ready read-only study session from a prepared material", async () => {
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        session_status: "ready",
        session_id: "study-session:doc-1",
        document_id: "doc-1",
        material_title: "Aula preparada",
        material_type: "study_material",
        summary_status: "ready",
        estimated_minutes: 10,
        sections_count: 2,
        items: [
          {
            section_id: "section-1",
            title: "Atos administrativos",
            summary: "Resumo em preparação para esta seção.",
            key_points: ["Atos administrativos"],
            estimated_minutes: 5,
            status: "ready"
          }
        ],
        next_actions: [
          { label: "Abrir material", href: "/materials/doc-1" },
          { label: "Ver materiais", href: "/materials" }
        ],
        message: "Este estudo ainda não está conectado completamente ao edital.",
        source: "user_scope"
      }
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Estudo de agora")).toBeInTheDocument();
    expect(screen.getByText("Aula preparada")).toBeInTheDocument();
    expect(screen.getByText("Atos administrativos")).toBeInTheDocument();
    expect(screen.getByText("Resumo em preparação para esta seção.")).toBeInTheDocument();
    expect(screen.getByText("Esta sessão ainda não altera seu progresso. Questões e revisão serão adicionadas depois.")).toBeInTheDocument();
    expect(screen.getByText("Abrir material")).toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
  });

  it("renders a friendly not-ready state when no prepared study material exists", async () => {
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        session_status: "not_ready",
        message: "Envie e prepare um material de estudo para começar.",
        next_actions: [{ label: "Enviar material", href: "/materials/upload" }],
        source: "user_scope"
      }
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Seu estudo ainda não está pronto.")).toBeInTheDocument();
    expect(screen.getByText("Envie e prepare um material de estudo para começar.")).toBeInTheDocument();
    expect(screen.getByText("Enviar material")).toBeInTheDocument();
    expect(screen.queryByText("Estudo de hoje")).not.toBeInTheDocument();
  });

  it("renders a safe auth-required state", async () => {
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "auth_required",
        message: "Entre para ver sua sessão de estudo."
      }
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Entre para ver sua sessão de estudo.")).toBeInTheDocument();
    expect(screen.getByText("Entrar")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    });
  });
});
