import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const nextStudySessionMock = vi.hoisted(() => ({
  fetchStudyBlocks: vi.fn(),
  fetchNextStudySession: vi.fn(),
  fetchNextReviewBlock: vi.fn(),
  fetchStudyProgressSummary: vi.fn(),
  createStudyProgressEvent: vi.fn()
}));

vi.mock("@/lib/api/study", () => ({
  fetchStudyBlocks: nextStudySessionMock.fetchStudyBlocks,
  fetchNextStudySession: nextStudySessionMock.fetchNextStudySession,
  fetchNextReviewBlock: nextStudySessionMock.fetchNextReviewBlock,
  fetchStudyProgressSummary: nextStudySessionMock.fetchStudyProgressSummary,
  createStudyProgressEvent: nextStudySessionMock.createStudyProgressEvent
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

function buildReadyReview(overrides: Record<string, unknown> = {}) {
  return {
    review_status: "ready",
    review_id: "review:prepared-materials:1",
    basis: "prepared_materials",
    materials_count: 3,
    blocks_count: 3,
    estimated_minutes: 18,
    title: "Revisão de atos administrativos",
    summary: {
      status: "ready",
      items: [
        {
          title: "Atos administrativos",
          message: "Revise os conceitos centrais dos blocos preparados.",
          topic_label: "Direito Administrativo",
          subtopic_label: "Atos administrativos"
        }
      ]
    },
    questions: {
      status: "ready",
      items_count: 5
    },
    reinforcement: {
      status: "needs_review",
      weak_topics_count: 1,
      items: [
        {
          topic_label: "Direito Administrativo",
          subtopic_label: "Atos administrativos",
          message: "Retome os pontos principais antes das questões de revisão."
        }
      ]
    },
    actions: [{ label: "Abrir revisão", href: "/study/review/review:prepared-materials:1" }],
    source: "user_scope",
    ...overrides
  };
}

function buildProgressSummary(overrides: Record<string, unknown> = {}) {
  return {
    progress_status: "ready",
    opened_blocks_count: 1,
    studied_blocks_count: 2,
    prepared_materials_count: 3,
    studied_materials_count: 0,
    review_due: true,
    review_basis: "prepared_materials",
    reviewed_questions_count: 4,
    weak_topics_count: 1,
    source: "user_scope",
    ...overrides
  };
}

describe("StudySessionWorkspaceClient next prepared material session", () => {
  beforeEach(() => {
    nextStudySessionMock.fetchStudyBlocks.mockReset();
    nextStudySessionMock.fetchNextStudySession.mockReset();
    nextStudySessionMock.fetchNextReviewBlock.mockReset();
    nextStudySessionMock.fetchStudyProgressSummary.mockReset();
    nextStudySessionMock.createStudyProgressEvent.mockReset();
    nextStudySessionMock.fetchNextReviewBlock.mockResolvedValue({
      ok: false,
      status: 200,
      source: "backend",
      error: {
        code: "not_ready",
        message: "Prepare pelo menos 3 materiais de estudo para montar uma revisão acumulada."
      }
    });
    nextStudySessionMock.fetchStudyProgressSummary.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: buildProgressSummary()
    });
  });

  it("renders connected edital study blocks before the one-material fallback", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        blocks_status: "ready",
        scope_status: "connected_to_edital",
        blocks_count: 1,
        estimated_minutes: 5,
        items: [
          {
            block_id: "block-1",
            title: "Atos administrativos",
            topic_id: "topic-1",
            topic_label: "Direito Administrativo",
            subtopic_id: "subtopic-1",
            subtopic_label: "Atos administrativos",
            material_id: "doc-1",
            material_title: "Aula preparada",
            sections_count: 1,
            summary_status: "ready",
            estimated_minutes: 5,
            status: "ready",
            actions: [{ label: "Estudar bloco", href: "/study/blocks/block-1" }]
          }
        ],
        source: "user_scope"
      }
    });
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        session_status: "ready",
        session_id: "study-session:doc-1",
        document_id: "doc-1",
        material_title: "Fallback antigo",
        material_type: "study_material",
        summary_status: "ready",
        estimated_minutes: 5,
        sections_count: 1,
        items: [],
        next_actions: [{ label: "Abrir material", href: "/materials/doc-1" }],
        message: "Comece por este material preparado.",
        source: "user_scope"
      }
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Seu caminho de estudo")).toBeInTheDocument();
    expect(screen.getAllByText("Conectado ao edital.").length).toBeGreaterThan(0);
    expect(screen.getByText("Atos administrativos")).toBeInTheDocument();
    expect(screen.getByText("Direito Administrativo · Atos administrativos")).toBeInTheDocument();
    expect(screen.getByText("Aula preparada")).toBeInTheDocument();
    expect(screen.getAllByText("5 min").length).toBeGreaterThan(0);
    expect(screen.getByText("Estudar bloco")).toBeInTheDocument();
    expect(screen.queryByText("Fallback antigo")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Concluir estudo")).not.toBeInTheDocument();
    expect(nextStudySessionMock.createStudyProgressEvent).not.toHaveBeenCalled();
  });

  it("renders a read-only progress summary card from explicit counts", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        blocks_status: "ready",
        scope_status: "material_only",
        blocks_count: 1,
        estimated_minutes: 6,
        items: [
          {
            block_id: "block-progress",
            title: "Bloco com acompanhamento",
            topic_id: null,
            topic_label: null,
            subtopic_id: null,
            subtopic_label: null,
            material_id: "doc-progress",
            material_title: "Material preparado",
            sections_count: 1,
            summary_status: "ready",
            estimated_minutes: 6,
            status: "ready",
            actions: []
          }
        ],
        source: "user_scope"
      }
    });
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: { code: "backend_offline", message: "Não foi possível carregar a sessão agora." }
    });
    nextStudySessionMock.fetchStudyProgressSummary.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: buildProgressSummary()
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Acompanhamento do estudo")).toBeInTheDocument();
    expect(screen.getByText("Resumo das ações registradas por você.")).toBeInTheDocument();
    expect(screen.getByText("Materiais preparados")).toBeInTheDocument();
    expect(screen.getByText("Blocos marcados como estudados")).toBeInTheDocument();
    expect(screen.getByText("Questões revisadas sem pontuação")).toBeInTheDocument();
    expect(screen.getByText("Blocos abertos")).toBeInTheDocument();
    expect(screen.getByText("Pontos para reforço")).toBeInTheDocument();
    expect(screen.getByText("Revisão sugerida com base em materiais preparados.")).toBeInTheDocument();
    expect(
      screen.getByText("Este resumo não conclui materiais automaticamente. Respostas oficiais e notas não fazem parte desta etapa.")
    ).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(nextStudySessionMock.fetchStudyProgressSummary).toHaveBeenCalledTimes(1);
    expect(nextStudySessionMock.createStudyProgressEvent).not.toHaveBeenCalled();
  });

  it("renders backend-provided studied-material review and progress basis without inferring it", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        blocks_status: "ready",
        scope_status: "material_only",
        blocks_count: 1,
        estimated_minutes: 6,
        items: [
          {
            block_id: "block-studied-review",
            title: "Bloco estudado",
            topic_id: null,
            topic_label: null,
            subtopic_id: null,
            subtopic_label: null,
            material_id: "doc-studied",
            material_title: "Material estudado",
            sections_count: 1,
            summary_status: "ready",
            estimated_minutes: 6,
            status: "ready",
            actions: []
          }
        ],
        source: "user_scope"
      }
    });
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: { code: "backend_offline", message: "Não foi possível carregar a sessão agora." }
    });
    nextStudySessionMock.fetchNextReviewBlock.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: buildReadyReview({
        review_id: "review:studied_materials:3:3",
        basis: "studied_materials",
        materials_count: 3
      })
    });
    nextStudySessionMock.fetchStudyProgressSummary.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: buildProgressSummary({
        studied_blocks_count: 8,
        studied_materials_count: 3,
        review_basis: "studied_materials"
      })
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Baseada em materiais estudados")).toBeInTheDocument();
    expect(screen.getByText("Materiais estudados")).toBeInTheDocument();
    expect(screen.getByText("Revisão sugerida com base em materiais estudados.")).toBeInTheDocument();
    expect(nextStudySessionMock.createStudyProgressEvent).not.toHaveBeenCalled();
    expect(document.body.textContent).not.toContain("material concluído");
    expect(document.body.textContent).not.toContain("progresso atualizado");
    expect(document.body.textContent).not.toContain("100%");
    expect(document.body.textContent).not.toContain("percentual");
    expect(document.body.textContent).not.toContain("gabarito");
    expect(document.body.textContent).not.toContain("resposta correta");
    expect(document.body.textContent).not.toContain("simulado");
  });

  it("does not infer studied materials from studied block counts", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        blocks_status: "ready",
        scope_status: "material_only",
        blocks_count: 1,
        estimated_minutes: 6,
        items: [
          {
            block_id: "block-no-inference",
            title: "Bloco sem inferência",
            topic_id: null,
            topic_label: null,
            subtopic_id: null,
            subtopic_label: null,
            material_id: "doc-no-inference",
            material_title: "Material preparado",
            sections_count: 1,
            summary_status: "ready",
            estimated_minutes: 6,
            status: "ready",
            actions: []
          }
        ],
        source: "user_scope"
      }
    });
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: { code: "backend_offline", message: "Não foi possível carregar a sessão agora." }
    });
    nextStudySessionMock.fetchNextReviewBlock.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: buildReadyReview({
        basis: "prepared_materials"
      })
    });
    nextStudySessionMock.fetchStudyProgressSummary.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: buildProgressSummary({
        studied_blocks_count: 12,
        studied_materials_count: 0,
        review_basis: "prepared_materials"
      })
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Baseada em materiais preparados")).toBeInTheDocument();
    expect(screen.getByText("Revisão sugerida com base em materiais preparados.")).toBeInTheDocument();
    expect(screen.queryByText("Materiais estudados")).not.toBeInTheDocument();
    expect(screen.queryByText("Revisão sugerida com base em materiais estudados.")).not.toBeInTheDocument();
    expect(nextStudySessionMock.createStudyProgressEvent).not.toHaveBeenCalled();
  });

  it("handles auth-required and unavailable progress summary states safely", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "auth_required",
        message: "Entre para ver seus blocos de estudo."
      }
    });
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "auth_required",
        message: "Entre para ver sua sessão de estudo."
      }
    });
    nextStudySessionMock.fetchStudyProgressSummary.mockResolvedValueOnce({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "auth_required",
        message: "Entre para acompanhar seu progresso."
      }
    });

    const { unmount } = render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Entre para acompanhar seu estudo.")).toBeInTheDocument();
    expect(nextStudySessionMock.createStudyProgressEvent).not.toHaveBeenCalled();

    unmount();
    nextStudySessionMock.fetchStudyProgressSummary.mockResolvedValueOnce({
      ok: false,
      status: 502,
      source: "offline",
      error: {
        code: "backend_offline",
        message: "Não foi possível carregar seu resumo de progresso agora."
      }
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Não foi possível carregar seu acompanhamento agora.")).toBeInTheDocument();
    expect(nextStudySessionMock.createStudyProgressEvent).not.toHaveBeenCalled();
  });

  it("renders material-only study blocks when edital scope is not connected", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        blocks_status: "partial",
        scope_status: "material_only",
        blocks_count: 1,
        estimated_minutes: 7,
        items: [
          {
            block_id: "block-material-1",
            title: "Leitura inicial",
            topic_id: null,
            topic_label: null,
            subtopic_id: null,
            subtopic_label: null,
            material_id: "doc-2",
            material_title: "Material sem edital",
            sections_count: 2,
            summary_status: "needs_review",
            estimated_minutes: 7,
            status: "needs_review",
            actions: []
          }
        ],
        source: "user_scope"
      }
    });
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: { code: "backend_offline", message: "Não foi possível carregar a sessão agora." }
    });

    render(<StudySessionWorkspaceClient />);

    expect(
      (await screen.findAllByText("Baseado nos materiais preparados. Ainda não conectado completamente ao edital.")).length
    ).toBeGreaterThan(0);
    expect(screen.getByText("Leitura inicial")).toBeInTheDocument();
    expect(screen.getByText("Material sem edital")).toBeInTheDocument();
    expect(screen.getAllByText("Precisa de conferência").length).toBeGreaterThan(0);
    expect(screen.getByText("Ver material")).toBeInTheDocument();
  });

  it("renders a ready read-only study session from a prepared material", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: { code: "backend_offline", message: "Não foi possível carregar seus blocos agora." }
    });
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
    expect(screen.getByText("Use esta orientação para organizar a leitura deste material.")).toBeInTheDocument();
    expect(screen.getByText("Abrir material")).toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
  });

  it("renders a ready cumulative review card without exposing a future review-detail route", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        blocks_status: "ready",
        scope_status: "material_only",
        blocks_count: 1,
        estimated_minutes: 7,
        items: [
          {
            block_id: "block-review-1",
            title: "Leitura base",
            topic_id: null,
            topic_label: null,
            subtopic_id: null,
            subtopic_label: null,
            material_id: "doc-3",
            material_title: "Material preparado",
            sections_count: 2,
            summary_status: "ready",
            estimated_minutes: 7,
            status: "ready",
            actions: [{ label: "Estudar bloco", href: "/study/blocks/block-review-1" }]
          }
        ],
        source: "user_scope"
      }
    });
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: { code: "backend_offline", message: "Não foi possível carregar a sessão agora." }
    });
    nextStudySessionMock.fetchNextReviewBlock.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: buildReadyReview()
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Revisão acumulada sugerida")).toBeInTheDocument();
    expect(screen.getByText("Use esta revisão para retomar pontos dos materiais preparados.")).toBeInTheDocument();
    expect(screen.getByText("Revisão de atos administrativos")).toBeInTheDocument();
    expect(screen.getByText("Baseada em materiais preparados")).toBeInTheDocument();
    expect(screen.getByText("Revise os conceitos centrais dos blocos preparados.")).toBeInTheDocument();
    expect(screen.getByText("Direito Administrativo · Atos administrativos")).toBeInTheDocument();
    expect(screen.getByText(/Questões de revisão disponíveis · 5 itens/)).toBeInTheDocument();
    expect(screen.getByText("Retome os pontos principais antes das questões de revisão.")).toBeInTheDocument();
    expect(screen.getByText("Esta revisão ainda não altera seu progresso. Ela não substitui o estudo dos blocos.")).toBeInTheDocument();
    expect(screen.getByText("Ver materiais")).toHaveAttribute("href", "/materials");
    expect(screen.queryByText("Abrir revisão")).not.toBeInTheDocument();
    expect(document.body.textContent).not.toContain("/study/review/");
    expect(document.body.textContent).not.toContain("gabarito");
    expect(document.body.textContent).not.toContain("answer_key");
    expect(document.body.textContent).not.toContain("score");
    expect(document.body.textContent).not.toContain("simulado");
  });

  it("renders a needs-review cumulative review card with safe question and reinforcement copy", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        blocks_status: "needs_review",
        scope_status: "material_only",
        blocks_count: 1,
        estimated_minutes: 8,
        items: [
          {
            block_id: "block-review-2",
            title: "Revisão de leitura",
            topic_id: "topic-2",
            topic_label: "Português",
            subtopic_id: null,
            subtopic_label: null,
            material_id: "doc-4",
            material_title: "Material de Português",
            sections_count: 1,
            summary_status: "needs_review",
            estimated_minutes: 8,
            status: "needs_review",
            actions: []
          }
        ],
        source: "user_scope"
      }
    });
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: { code: "backend_offline", message: "Não foi possível carregar a sessão agora." }
    });
    nextStudySessionMock.fetchNextReviewBlock.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: buildReadyReview({
        review_status: "needs_review",
        basis: "study_blocks",
        questions: { status: "needs_review", items_count: 2 },
        reinforcement: {
          status: "needs_review",
          weak_topics_count: 0,
          items: [
            {
              topic_label: null,
              subtopic_label: null,
              message: "Ainda não há histórico suficiente para destacar pontos fracos reais."
            }
          ]
        }
      })
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Revisão acumulada sugerida")).toBeInTheDocument();
    expect(screen.getByText("Baseada em blocos disponíveis")).toBeInTheDocument();
    expect(screen.getAllByText("Precisa de conferência").length).toBeGreaterThan(0);
    expect(screen.getByText(/Questões de revisão em conferência · 2 itens/)).toBeInTheDocument();
    expect(screen.getByText("Ainda não há histórico suficiente para destacar pontos fracos reais.")).toBeInTheDocument();
    expect(screen.queryByText("Pontuação")).not.toBeInTheDocument();
  });

  it("renders a partial cumulative review state without studied or completed claims", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: false,
      status: 200,
      source: "backend",
      error: {
        code: "not_ready",
        message: "Envie e prepare um material de estudo para montar seus blocos."
      }
    });
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: false,
      status: 200,
      source: "backend",
      error: {
        code: "not_ready",
        message: "Envie e prepare um material de estudo para começar."
      }
    });
    nextStudySessionMock.fetchNextReviewBlock.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: buildReadyReview({
        review_status: "partial",
        materials_count: 2,
        blocks_count: 2,
        estimated_minutes: 11,
        summary: { status: "needs_review", items: [] },
        questions: { status: "not_ready", items_count: 0 },
        reinforcement: { status: "not_ready", weak_topics_count: 0, items: [] }
      })
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Revisão acumulada em preparação.")).toBeInTheDocument();
    expect(screen.getByText("Prepare mais materiais para uma revisão mais completa.")).toBeInTheDocument();
    expect(screen.getByText("Esta revisão ainda não altera seu progresso. Ela não substitui o estudo dos blocos.")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("materiais estudados");
    expect(document.body.textContent).not.toContain("materiais concluídos");
    expect(document.body.textContent).not.toContain("progresso atualizado");
  });

  it("keeps the not-ready cumulative review state compact when study blocks already exist", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        blocks_status: "ready",
        scope_status: "material_only",
        blocks_count: 1,
        estimated_minutes: 6,
        items: [
          {
            block_id: "block-compact",
            title: "Bloco disponível",
            topic_id: null,
            topic_label: null,
            subtopic_id: null,
            subtopic_label: null,
            material_id: "doc-compact",
            material_title: "Material compacto",
            sections_count: 1,
            summary_status: "ready",
            estimated_minutes: 6,
            status: "ready",
            actions: []
          }
        ],
        source: "user_scope"
      }
    });
    nextStudySessionMock.fetchNextStudySession.mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: { code: "backend_offline", message: "Não foi possível carregar a sessão agora." }
    });

    render(<StudySessionWorkspaceClient />);

    expect(await screen.findByText("Bloco disponível")).toBeInTheDocument();
    expect(screen.queryByText("Prepare pelo menos 3 materiais de estudo para montar uma revisão acumulada.")).not.toBeInTheDocument();
  });

  it("renders a friendly not-ready state when no prepared study material exists", async () => {
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: false,
      status: 200,
      source: "backend",
      error: {
        code: "not_ready",
        message: "Envie e prepare um material de estudo para montar seus blocos."
      }
    });
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
    nextStudySessionMock.fetchStudyBlocks.mockResolvedValue({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "auth_required",
        message: "Entre para ver seus blocos de estudo."
      }
    });
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
