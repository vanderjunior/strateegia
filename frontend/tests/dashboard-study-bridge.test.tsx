import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/adapters/study-sessions", async () => {
  const actual = await vi.importActual<typeof import("@/lib/adapters/study-sessions")>(
    "@/lib/adapters/study-sessions"
  );

  return {
    ...actual,
    loadStudySessionWorkspaceViewModel: vi.fn(async () => actual.buildMockStudySessionWorkspaceViewModel())
  };
});

import { DashboardStudyBridge } from "@/components/dashboard/DashboardStudyBridge";

describe("DashboardStudyBridge", () => {
  it("renders read-only study guidance and avoids mutation CTAs", async () => {
    render(<DashboardStudyBridge />);

    expect(screen.getAllByText(/estudo de hoje/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Sessão sugerida")).toBeInTheDocument();
    expect(screen.getByText("Não altera seu progresso")).toBeInTheDocument();
    expect(await screen.findAllByText("Abrir orientação")).not.toHaveLength(0);

    expect(screen.queryByText("Começar sessão")).not.toBeInTheDocument();
    expect(screen.queryByText("Concluir sessão")).not.toBeInTheDocument();
    expect(screen.queryByText("Marcar como feito")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
    expect(screen.queryByText("Agendar")).not.toBeInTheDocument();
  });
});
