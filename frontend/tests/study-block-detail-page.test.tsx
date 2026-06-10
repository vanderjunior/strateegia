import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const studyBlockDetailMock = vi.hoisted(() => ({
  createStudyProgressEvent: vi.fn(),
  fetchStudyBlockDetail: vi.fn(),
  fetchStudyBlockQuestions: vi.fn(),
  reviewStudyBlockQuestionAnswer: vi.fn()
}));

vi.mock("@/lib/api/study", () => ({
  createStudyProgressEvent: studyBlockDetailMock.createStudyProgressEvent,
  fetchStudyBlockDetail: studyBlockDetailMock.fetchStudyBlockDetail,
  fetchStudyBlockQuestions: studyBlockDetailMock.fetchStudyBlockQuestions,
  reviewStudyBlockQuestionAnswer: studyBlockDetailMock.reviewStudyBlockQuestionAnswer
}));

import StudyBlockDetailPage from "@/app/(app)/study/blocks/[blockId]/page";
import { StudyBlockDetailReadOnlyClient } from "@/components/workspace/StudyBlockDetailReadOnlyClient";

function readyDetail(overrides: Record<string, unknown> = {}) {
  return {
    block_id: "study-block:topic-1:doc-1:0",
    detail_status: "ready",
    title: "Atos administrativos",
    topic_id: "topic-1",
    topic_label: "Direito Administrativo",
    subtopic_id: "subtopic-1",
    subtopic_label: "Atos administrativos",
    material_id: "doc-1",
    material_title: "Aula preparada",
    summary_status: "ready",
    estimated_minutes: 5,
    sections: [
      {
        section_id: "section-1",
        title: "Conceitos principais",
        summary: "Resumo em preparação para esta seção.",
        key_points: ["Atos administrativos", "Poderes administrativos"],
        estimated_minutes: 5,
        status: "ready"
      }
    ],
    actions: [
      { label: "Abrir material", href: "/materials/doc-1" },
      { label: "Voltar ao caminho de estudo", href: "/study" }
    ],
    source: "user_scope",
    ...overrides
  };
}

function readyQuestions(overrides: Record<string, unknown> = {}) {
  return {
    block_id: "study-block:topic-1:doc-1:0",
    question_status: "ready",
    mode: "review_only",
    items: [
      {
        question_id: "question:study-block:topic-1:doc-1:0:0",
        type: "multiple_choice",
        prompt: "Considerando o tema Direito Administrativo, escolha uma alternativa para orientar sua revisão de Atos administrativos.",
        alternatives: [
          { id: "A", text: "Revisar Atos administrativos." },
          { id: "B", text: "Relacionar Direito Administrativo ao resumo do bloco." },
          { id: "C", text: "Identificar pontos principais de Atos administrativos." },
          { id: "D", text: "Retomar Direito Administrativo no material estudado." },
          { id: "E", text: "Comparar Atos administrativos com os demais pontos do bloco." }
        ],
        topic_label: "Direito Administrativo",
        subtopic_label: "Atos administrativos",
        difficulty: "basic",
        status: "candidate"
      }
    ],
    warnings_count: 0,
    source: "user_scope",
    ...overrides
  };
}

function reviewedAnswer(overrides: Record<string, unknown> = {}) {
  return {
    block_id: "study-block:topic-1:doc-1:0",
    question_id: "question:study-block:topic-1:doc-1:0:0",
    review_status: "reviewed",
    result: "ungraded",
    feedback: "Compare sua escolha com o resumo do bloco.",
    reinforcement: {
      topic_label: "Direito Administrativo",
      subtopic_label: "Atos administrativos",
      message: "Revise o resumo do bloco e compare sua resposta com os pontos principais de Atos administrativos.",
      suggested_action: "review_summary"
    },
    source: "user_scope",
    ...overrides
  };
}

function progressEventResponse(overrides: Record<string, unknown> = {}) {
  return {
    event_id: "progress-event-1",
    event_type: "block_marked_studied",
    target_type: "block",
    target_id: "study-block:topic-1:doc-1:0",
    created_at: "2026-06-10T12:00:00Z",
    source: "user_scope",
    ...overrides
  };
}

describe("StudyBlockDetailReadOnlyClient", () => {
  beforeEach(() => {
    studyBlockDetailMock.createStudyProgressEvent.mockReset();
    studyBlockDetailMock.fetchStudyBlockDetail.mockReset();
    studyBlockDetailMock.fetchStudyBlockQuestions.mockReset();
    studyBlockDetailMock.reviewStudyBlockQuestionAnswer.mockReset();
    studyBlockDetailMock.createStudyProgressEvent.mockResolvedValue({
      ok: true,
      status: 201,
      source: "backend",
      data: progressEventResponse()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: false,
      status: 200,
      source: "backend",
      error: {
        code: "not_ready",
        message: "As questões ainda não estão prontas para este bloco."
      }
    });
    studyBlockDetailMock.reviewStudyBlockQuestionAnswer.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: reviewedAnswer()
    });
  });

  it("renders ready block detail with topic, material, sections, key points, safe actions, and questions", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    expect(await screen.findByText("Estudar bloco")).toBeInTheDocument();
    expect(screen.getAllByText("Atos administrativos").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pronto para estudo").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Direito Administrativo · Atos administrativos").length).toBeGreaterThan(0);
    expect(screen.getByText("Aula preparada")).toBeInTheDocument();
    expect(screen.getAllByText("5 min").length).toBeGreaterThan(0);
    expect(screen.getByText("Resumo do bloco")).toBeInTheDocument();
    expect(screen.getByText("Conceitos principais")).toBeInTheDocument();
    expect(screen.getByText("Resumo em preparação para esta seção.")).toBeInTheDocument();
    expect(screen.getAllByText(/Atos administrativos$/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Poderes administrativos$/)).toBeInTheDocument();
    expect(screen.getByText("Abrir material")).toHaveAttribute("href", "/materials/doc-1");
    expect(screen.getByText("Voltar ao caminho de estudo")).toHaveAttribute("href", "/study");
    expect(screen.getByText("Use este bloco como guia inicial de leitura.")).toBeInTheDocument();
    expect(screen.getByText("Esta tela mostra apenas uma orientação de leitura para este bloco.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Marcar bloco como estudado" })).toBeInTheDocument();
    expect(screen.getByText("Esta ação registra apenas este bloco. Ela não conclui o material.")).toBeInTheDocument();
    expect(await screen.findByText("Questões de fixação")).toBeInTheDocument();
    expect(screen.getByText("Use estas questões como revisão inicial do bloco. Elas ainda não exibem respostas oficiais nem avaliam respostas.")).toBeInTheDocument();
    expect(screen.getByText("Múltipla escolha · Básica")).toBeInTheDocument();
    expect(screen.getByText("1. Considerando o tema Direito Administrativo, escolha uma alternativa para orientar sua revisão de Atos administrativos.")).toBeInTheDocument();
    expect(screen.getByText("A. Revisar Atos administrativos.")).toBeInTheDocument();
    expect(screen.getByText("E. Comparar Atos administrativos com os demais pontos do bloco.")).toBeInTheDocument();
    expect(screen.getByText("Escolha uma alternativa")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "A. Revisar Atos administrativos." })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "E. Comparar Atos administrativos com os demais pontos do bloco." })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revisar escolha" })).toBeInTheDocument();
    expect(screen.getByText("Questão candidata")).toBeInTheDocument();
    expect(screen.getByText("Sem respostas oficiais nesta etapa")).toBeInTheDocument();
  });

  it("does not record progress on render", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    expect(await screen.findByRole("button", { name: "Marcar bloco como estudado" })).toBeInTheDocument();
    expect(studyBlockDetailMock.createStudyProgressEvent).not.toHaveBeenCalled();
  });

  it("records explicit block_marked_studied progress only when the button is clicked", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("button", { name: "Marcar bloco como estudado" }));

    await waitFor(() => {
      expect(studyBlockDetailMock.createStudyProgressEvent).toHaveBeenCalledTimes(1);
      expect(studyBlockDetailMock.createStudyProgressEvent).toHaveBeenCalledWith({
        event_type: "block_marked_studied",
        target_type: "block",
        target_id: "study-block:topic-1:doc-1:0",
        idempotency_key: "block_marked_studied:study-block:topic-1:doc-1:0"
      });
    });
    expect(await screen.findByText("Bloco marcado como estudado.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Estudo registrado" })).toBeDisabled();
  });

  it("renders loading state while registering explicit block progress", async () => {
    let resolveProgress: (value: unknown) => void = () => undefined;
    studyBlockDetailMock.createStudyProgressEvent.mockReturnValue(
      new Promise((resolve) => {
        resolveProgress = resolve;
      })
    );
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("button", { name: "Marcar bloco como estudado" }));

    expect(await screen.findByRole("button", { name: "Registrando estudo..." })).toBeDisabled();
    await act(async () => {
      resolveProgress({
        ok: true,
        status: 201,
        source: "backend",
        data: progressEventResponse()
      });
    });
  });

  it.each([
    ["auth_required", "Entre para registrar seu estudo."],
    ["invalid_request", "Não foi possível registrar este bloco."],
    ["backend_offline", "Não foi possível registrar esta ação agora."],
    ["missing_base_url", "Não foi possível registrar esta ação agora."],
    ["invalid_response", "Não foi possível registrar esta ação agora."]
  ])("renders %s progress registration state safely", async (code, message) => {
    studyBlockDetailMock.createStudyProgressEvent.mockResolvedValue({
      ok: false,
      status: code === "auth_required" ? 401 : 502,
      source: code === "backend_offline" ? "offline" : "backend",
      error: { code, message: "Mensagem técnica que não deve aparecer." }
    });
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("button", { name: "Marcar bloco como estudado" }));

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.queryByText("Mensagem técnica que não deve aparecer.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Marcar bloco como estudado" })).toBeEnabled();
  });

  it("renders multiple-choice A-D when only four alternatives are returned", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions({
        items: [
          {
            ...readyQuestions().items[0],
            alternatives: [
              { id: "A", text: "Revisar Atos administrativos." },
              { id: "B", text: "Relacionar Atos administrativos ao resumo do bloco." },
              { id: "C", text: "Identificar pontos principais de Atos administrativos." },
              { id: "D", text: "Retomar Atos administrativos no material estudado." }
            ]
          }
        ]
      })
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    expect(await screen.findByRole("radio", { name: "A. Revisar Atos administrativos." })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "D. Retomar Atos administrativos no material estudado." })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: /E\./ })).not.toBeInTheDocument();
  });

  it("renders needs-review block and question candidates safely", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail({
        detail_status: "needs_review",
        summary_status: "needs_review",
        topic_id: null,
        topic_label: null,
        subtopic_id: null,
        subtopic_label: null,
        sections: [
          {
            section_id: "section-1",
            title: "Leitura inicial",
            summary: "Resumo em preparação para esta seção.",
            key_points: [],
            estimated_minutes: 4,
            status: "needs_review"
          }
        ]
      })
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions({
        question_status: "needs_review",
        items: [
          {
            ...readyQuestions().items[0],
            type: "true_false",
            prompt: "Considere o ponto Leitura inicial como foco de revisão deste bloco.",
            alternatives: [
              { id: "C", text: "Certo" },
              { id: "E", text: "Errado" }
            ],
            topic_label: null,
            subtopic_label: null,
            difficulty: "medium",
            status: "needs_review"
          }
        ],
        warnings_count: 1
      })
    });

    render(<StudyBlockDetailReadOnlyClient blockId="block-1" />);

    expect((await screen.findAllByText("Precisa de conferência")).length).toBeGreaterThan(0);
    expect(screen.getByText("Leitura inicial")).toBeInTheDocument();
    expect(screen.queryByText("Direito Administrativo · Atos administrativos")).not.toBeInTheDocument();
    expect(screen.getByText("Estas questões precisam de conferência.")).toBeInTheDocument();
    expect(screen.getByText("Certo ou errado · Média")).toBeInTheDocument();
    expect(screen.getByText("C. Certo")).toBeInTheDocument();
    expect(screen.getByText("E. Errado")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "C. Certo" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "E. Errado" })).toBeInTheDocument();
  });

  it("shows a validation message when reviewing without a selected option", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("button", { name: "Revisar escolha" }));

    expect(screen.getByText("Selecione uma alternativa antes de revisar.")).toBeInTheDocument();
    expect(studyBlockDetailMock.reviewStudyBlockQuestionAnswer).not.toHaveBeenCalled();
  });

  it("submits a multiple-choice selection as a choice review", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("radio", { name: "A. Revisar Atos administrativos." }));
    fireEvent.click(screen.getByRole("button", { name: "Revisar escolha" }));

    await waitFor(() => {
      expect(studyBlockDetailMock.reviewStudyBlockQuestionAnswer).toHaveBeenCalledWith(
        "study-block:topic-1:doc-1:0",
        "question:study-block:topic-1:doc-1:0:0",
        { answer: "A", answer_format: "choice" }
      );
    });
  });

  it("submits a true/false selection with true_false answer format", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions({
        items: [
          {
            ...readyQuestions().items[0],
            type: "true_false",
            prompt: "Considere o ponto Atos administrativos como foco de revisão deste bloco.",
            alternatives: [
              { id: "C", text: "Certo" },
              { id: "E", text: "Errado" }
            ]
          }
        ]
      })
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("radio", { name: "C. Certo" }));
    fireEvent.click(screen.getByRole("button", { name: "Revisar escolha" }));

    await waitFor(() => {
      expect(studyBlockDetailMock.reviewStudyBlockQuestionAnswer).toHaveBeenCalledWith(
        "study-block:topic-1:doc-1:0",
        "question:study-block:topic-1:doc-1:0:0",
        { answer: "C", answer_format: "true_false" }
      );
    });
  });

  it("renders loading state while reviewing a selected option", async () => {
    let resolveReview: (value: unknown) => void = () => undefined;
    studyBlockDetailMock.reviewStudyBlockQuestionAnswer.mockReturnValue(
      new Promise((resolve) => {
        resolveReview = resolve;
      })
    );
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("radio", { name: "A. Revisar Atos administrativos." }));
    fireEvent.click(screen.getByRole("button", { name: "Revisar escolha" }));

    expect(await screen.findByRole("button", { name: "Revisando escolha..." })).toBeDisabled();
    await act(async () => {
      resolveReview({
        ok: true,
        status: 200,
        source: "backend",
        data: reviewedAnswer()
      });
    });
  });

  it("renders conservative feedback and reinforcement after successful review", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("radio", { name: "A. Revisar Atos administrativos." }));
    fireEvent.click(screen.getByRole("button", { name: "Revisar escolha" }));

    expect(await screen.findByText("Feedback")).toBeInTheDocument();
    expect(screen.getByText("Escolha revisada sem pontuação.")).toBeInTheDocument();
    expect(screen.getByText("Compare sua escolha com o resumo do bloco.")).toBeInTheDocument();
    expect(screen.getByText("Reforço sugerido")).toBeInTheDocument();
    expect(screen.getAllByText("Direito Administrativo · Atos administrativos").length).toBeGreaterThan(0);
    expect(screen.getByText("Revise o resumo do bloco e compare sua resposta com os pontos principais de Atos administrativos.")).toBeInTheDocument();
    expect(screen.getByText("Revisar resumo")).toBeInTheDocument();
    expect(screen.getByText("Este feedback é uma orientação de estudo, não uma correção oficial.")).toBeInTheDocument();
    expect(screen.getByText("Seu progresso ainda não é alterado nesta etapa.")).toBeInTheDocument();
  });

  it("renders needs-review feedback safely", async () => {
    studyBlockDetailMock.reviewStudyBlockQuestionAnswer.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: reviewedAnswer({
        review_status: "needs_review",
        result: "needs_review",
        feedback: "Esta questão ainda não tem uma regra segura de revisão automática.",
        reinforcement: {
          topic_label: null,
          subtopic_label: null,
          message: "Revise o resumo do bloco antes de avançar.",
          suggested_action: "revisit_block"
        }
      })
    });
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("radio", { name: "A. Revisar Atos administrativos." }));
    fireEvent.click(screen.getByRole("button", { name: "Revisar escolha" }));

    expect(await screen.findByText("Esta escolha precisa de conferência.")).toBeInTheDocument();
    expect(screen.getByText("Revisitar bloco")).toBeInTheDocument();
    expect(screen.getByText("Este feedback é uma orientação de estudo, não uma correção oficial.")).toBeInTheDocument();
  });

  it("maps retry reinforcement action safely", async () => {
    studyBlockDetailMock.reviewStudyBlockQuestionAnswer.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: reviewedAnswer({
        reinforcement: {
          topic_label: "Direito Administrativo",
          subtopic_label: "Atos administrativos",
          message: "Tente a questão novamente depois de revisar os pontos principais.",
          suggested_action: "retry_question"
        }
      })
    });
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("radio", { name: "A. Revisar Atos administrativos." }));
    fireEvent.click(screen.getByRole("button", { name: "Revisar escolha" }));

    expect(await screen.findByText("Reforço sugerido")).toBeInTheDocument();
    expect(screen.getByText("Tentar novamente")).toBeInTheDocument();
    expect(screen.getByText("Tente a questão novamente depois de revisar os pontos principais.")).toBeInTheDocument();
  });

  it("shows a safe reinforcement fallback when the message is empty", async () => {
    studyBlockDetailMock.reviewStudyBlockQuestionAnswer.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: reviewedAnswer({
        reinforcement: {
          topic_label: null,
          subtopic_label: null,
          message: "   ",
          suggested_action: "review_summary"
        }
      })
    });
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("radio", { name: "A. Revisar Atos administrativos." }));
    fireEvent.click(screen.getByRole("button", { name: "Revisar escolha" }));

    expect(await screen.findByText("Reforço sugerido")).toBeInTheDocument();
    expect(
      screen.getByText("Revise o resumo do bloco e os pontos principais antes de tentar novamente.")
    ).toBeInTheDocument();
  });

  it.each([
    ["auth_required", "Entre para revisar sua escolha."],
    ["not_found", "Questão ou bloco de estudo não encontrado."],
    ["validation_error", "Revise sua escolha antes de enviar."],
    ["backend_offline", "Não foi possível revisar sua escolha agora."],
    ["missing_base_url", "Não foi possível revisar sua escolha agora."]
  ])("renders %s answer review state safely", async (code, message) => {
    studyBlockDetailMock.reviewStudyBlockQuestionAnswer.mockResolvedValue({
      ok: false,
      status: code === "not_found" ? 404 : 502,
      source: code === "backend_offline" ? "offline" : "backend",
      error: { code, message: "Mensagem técnica que não deve aparecer." }
    });
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    fireEvent.click(await screen.findByRole("radio", { name: "A. Revisar Atos administrativos." }));
    fireEvent.click(screen.getByRole("button", { name: "Revisar escolha" }));

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.queryByText("Mensagem técnica que não deve aparecer.")).not.toBeInTheDocument();
  });

  it("keeps short-answer fallback non-interactive", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyQuestions({
        items: [
          {
            ...readyQuestions().items[0],
            type: "short_answer",
            prompt: "Explique, com suas palavras, o ponto principal relacionado a Atos administrativos.",
            alternatives: []
          }
        ]
      })
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    expect(await screen.findByText("Resposta curta · Básica")).toBeInTheDocument();
    expect(screen.getByText("Revisão interativa ainda não disponível para este tipo de questão.")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Revisar escolha" })).not.toBeInTheDocument();
  });

  it("renders not-ready state safely", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: false,
      status: 200,
      source: "backend",
      error: {
        code: "not_ready",
        message: "Este bloco ainda não está pronto para estudo."
      }
    });

    render(<StudyBlockDetailReadOnlyClient blockId="block-1" />);

    expect((await screen.findAllByText("Este bloco ainda não está pronto para estudo.")).length).toBeGreaterThan(0);
    expect(screen.getByText("Volte ao caminho de estudo ou prepare o material relacionado.")).toBeInTheDocument();
    expect(screen.getByText("Voltar ao caminho de estudo")).toHaveAttribute("href", "/study");
  });

  it("renders not-ready questions safely for a ready block", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: false,
      status: 200,
      source: "backend",
      error: {
        code: "not_ready",
        message: "As questões ainda não estão prontas para este bloco."
      }
    });

    render(<StudyBlockDetailReadOnlyClient blockId="block-1" />);

    expect(await screen.findByText("Questões de fixação")).toBeInTheDocument();
    expect(screen.getByText("As questões ainda não estão prontas para este bloco.")).toBeInTheDocument();
    expect(screen.getByText("Estude o resumo do bloco primeiro.")).toBeInTheDocument();
  });

  it.each([
    ["auth_required", "Entre para ver as questões deste bloco."],
    ["not_found", "Bloco de estudo não encontrado."],
    ["backend_offline", "Não foi possível carregar as questões agora."],
    ["missing_base_url", "Não foi possível carregar as questões agora."]
  ])("renders %s question state safely", async (code, message) => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: false,
      status: code === "not_found" ? 404 : 502,
      source: code === "backend_offline" ? "offline" : "backend",
      error: { code, message: "Mensagem técnica que não deve aparecer." }
    });

    render(<StudyBlockDetailReadOnlyClient blockId="block-1" />);

    expect(await screen.findByText("Questões de fixação")).toBeInTheDocument();
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(screen.queryByText("Mensagem técnica que não deve aparecer.")).not.toBeInTheDocument();
  });

  it.each([
    ["auth_required", "Entre para ver este bloco de estudo.", "Entrar"],
    ["not_found", "Bloco de estudo não encontrado.", "Voltar ao caminho de estudo"],
    ["backend_offline", "Não foi possível carregar este bloco agora.", "Voltar ao caminho de estudo"],
    ["missing_base_url", "Não foi possível carregar este bloco agora.", "Voltar ao caminho de estudo"]
  ])("renders %s state safely", async (code, message, actionLabel) => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: false,
      status: code === "not_found" ? 404 : 502,
      source: code === "backend_offline" ? "offline" : "backend",
      error: { code, message: "Mensagem técnica que não deve aparecer." }
    });

    render(<StudyBlockDetailReadOnlyClient blockId="block-1" />);

    expect((await screen.findAllByText(message)).length).toBeGreaterThan(0);
    expect(screen.getByText(actionLabel)).toBeInTheDocument();
  });

  it("does not render raw or mutation-oriented fields", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="block-1" />);

    await screen.findByText("Resumo do bloco");
    const serialized = document.body.textContent ?? "";
    expect(serialized).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(serialized).not.toContain("chunk body");
    expect(serialized).not.toContain("section body");
    expect(serialized).not.toContain("storage_path");
    expect(serialized).not.toContain("/Users/");
    expect(serialized).not.toContain("token");
    expect(serialized).not.toContain("gabarito");
    expect(serialized).not.toContain("evidence");
    expect(serialized).not.toContain("answer_key");
    expect(serialized).not.toContain("correct_answer");
    expect(serialized).not.toContain("resposta correta");
    expect(serialized).not.toContain("correction");
    expect(serialized).not.toContain("score");
    expect(serialized).not.toContain("Você errou");
    expect(serialized).not.toContain("Você acertou");
    expect(serialized).not.toContain("pontuação");
    expect(serialized).not.toContain("Concluir estudo");
    expect(serialized).not.toContain("Concluir material");
    expect(serialized).not.toContain("Marcar material como concluído");
    expect(serialized).not.toContain("material concluído");
    expect(serialized).not.toContain("você concluiu");
    expect(serialized).not.toContain("progresso atualizado");
    expect(serialized).not.toContain("100%");
    expect(serialized).not.toContain("Gerar questões");
    expect(serialized).not.toContain("Gerar simulado");
    expect(serialized).not.toContain("Aplicar progresso");
    expect(serialized).not.toContain("Marcar progresso");
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /responder|corrigir|concluir|progresso|simulado|material/i })
    ).not.toBeInTheDocument();
  });
});

describe("StudyBlockDetailPage", () => {
  beforeEach(() => {
    studyBlockDetailMock.createStudyProgressEvent.mockReset();
    studyBlockDetailMock.fetchStudyBlockDetail.mockReset();
    studyBlockDetailMock.fetchStudyBlockQuestions.mockReset();
    studyBlockDetailMock.fetchStudyBlockQuestions.mockResolvedValue({
      ok: false,
      status: 200,
      source: "backend",
      error: {
        code: "not_ready",
        message: "As questões ainda não estão prontas para este bloco."
      }
    });
  });

  it("decodes block ids with colon before calling the API helper", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });

    render(
      await StudyBlockDetailPage({
        params: Promise.resolve({ blockId: "study-block%3Atopic-1%3Adoc-1%3A0" })
      })
    );

    await waitFor(() => {
      expect(studyBlockDetailMock.fetchStudyBlockDetail).toHaveBeenCalledWith("study-block:topic-1:doc-1:0");
    });
  });
});
