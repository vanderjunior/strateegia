import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const studyBlockDetailMock = vi.hoisted(() => ({
  fetchStudyBlockDetail: vi.fn()
}));

vi.mock("@/lib/api/study", () => ({
  fetchStudyBlockDetail: studyBlockDetailMock.fetchStudyBlockDetail
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

describe("StudyBlockDetailReadOnlyClient", () => {
  beforeEach(() => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockReset();
  });

  it("renders ready block detail with topic, material, sections, key points, and safe actions", async () => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: readyDetail()
    });

    render(<StudyBlockDetailReadOnlyClient blockId="study-block:topic-1:doc-1:0" />);

    expect(await screen.findByText("Estudar bloco")).toBeInTheDocument();
    expect(screen.getAllByText("Atos administrativos").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pronto para estudo").length).toBeGreaterThan(0);
    expect(screen.getByText("Direito Administrativo · Atos administrativos")).toBeInTheDocument();
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
  });

  it("renders needs-review status safely", async () => {
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

    render(<StudyBlockDetailReadOnlyClient blockId="block-1" />);

    expect((await screen.findAllByText("Precisa de conferência")).length).toBeGreaterThan(0);
    expect(screen.getByText("Leitura inicial")).toBeInTheDocument();
    expect(screen.queryByText("Direito Administrativo · Atos administrativos")).not.toBeInTheDocument();
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
    expect(serialized).not.toContain("Concluir estudo");
    expect(serialized).not.toContain("Gerar questões");
    expect(serialized).not.toContain("Gerar simulado");
    expect(serialized).not.toContain("Aplicar progresso");
    expect(serialized).not.toContain("Marcar progresso");
  });
});

describe("StudyBlockDetailPage", () => {
  beforeEach(() => {
    studyBlockDetailMock.fetchStudyBlockDetail.mockReset();
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
