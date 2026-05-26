import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/adapters/pscpp", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/pscpp")>(
    "@/lib/adapters/pscpp"
  );

  return {
    ...actual,
    loadPscppWorkspaceViewModel: vi.fn(async () => actual.buildMockPscppWorkspaceViewModel()),
    loadPscppCycleViewModel: vi.fn(async () => actual.buildMockPscppCycleViewModel()),
    loadPscppQuestionsViewModel: vi.fn(async () => actual.buildMockPscppQuestionsViewModel())
  };
});

vi.mock("@/lib/adapters/study-sessions", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/study-sessions")>(
    "@/lib/adapters/study-sessions"
  );

  return {
    ...actual,
    loadStudySessionWorkspaceViewModel: vi.fn(async () => actual.buildMockStudySessionWorkspaceViewModel()),
    loadStudySessionDetail: vi.fn(async (sessionId: string) => actual.buildMockStudySessionDetail(sessionId))
  };
});

import { PscppWorkspaceClient } from "@/components/workspace/PscppWorkspaceClient";
import { PscppCycleClient } from "@/components/workspace/PscppCycleClient";
import { PscppQuestionsClient } from "@/components/workspace/PscppQuestionsClient";
import { StudySessionWorkspaceClient } from "@/components/workspace/StudySessionWorkspaceClient";
import { StudySessionDetailClient } from "@/components/workspace/StudySessionDetailClient";

describe("PSCPP and study workspace copy", () => {
  it("keeps PSCPP and study surfaces in product language", async () => {
    render(
      <div>
        <PscppWorkspaceClient />
        <PscppCycleClient />
        <PscppQuestionsClient />
        <StudySessionWorkspaceClient />
      </div>
    );

    expect((await screen.findAllByText("Perfil PSCPP configurado")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ciclo sugerido").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Questões candidatas").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Guia flexível").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Estudo de hoje").length).toBeGreaterThan(0);
    expect(screen.getByText("Não altera seu progresso")).toBeInTheDocument();

    expect(screen.queryByText(/question-style profile/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/study-cycle profile/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\bmetadata\b/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\bledger\b/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\bguardrail\b/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\bpropagation\b/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\bworkspace\b/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
    expect(screen.queryByText("Agendar")).not.toBeInTheDocument();
  });

  it("keeps session 12 explicit about non-executable simulado limits", async () => {
    render(<StudySessionDetailClient sessionId="session-12-simulado-curto-revisao" />);

    expect(await screen.findByText(/Simulado curto ainda não executável/i)).toBeInTheDocument();
    expect(screen.getByText(/Questões candidatas ainda exigem revisão/i)).toBeInTheDocument();
    expect(screen.getByText(/Esta tela não gera prova nem corrige respostas/i)).toBeInTheDocument();
    expect(screen.queryByText("Começar sessão")).not.toBeInTheDocument();
    expect(screen.queryByText("Concluir sessão")).not.toBeInTheDocument();
  });
});
