import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { SessionState } from "@/lib/api/types";

const sessionMock = vi.hoisted(() => ({
  state: {
    status: "unauthenticated",
    label: "Entrar para continuar",
    description: "Entre para acessar seus materiais.",
    source: "backend"
  } as SessionState
}));

vi.mock("@/lib/adapters/session", () => ({
  buildDefaultSessionState: vi.fn(() => sessionMock.state),
  loadSessionState: vi.fn(async () => sessionMock.state)
}));

import { OnboardingReadOnlyClient } from "@/components/workspace/OnboardingReadOnlyClient";

describe("OnboardingReadOnlyClient", () => {
  beforeEach(() => {
    sessionMock.state = {
      status: "unauthenticated",
      label: "Entrar para continuar",
      description: "Entre para acessar seus materiais.",
      source: "backend"
    };
  });

  it("renders the first-use path with safe links and no mutation CTAs", async () => {
    render(<OnboardingReadOnlyClient />);

    expect(screen.getByText("Comece sua preparação")).toBeInTheDocument();
    expect(screen.getByText("Entre na sua conta")).toBeInTheDocument();
    expect(screen.getByText("Envie seu edital")).toBeInTheDocument();
    expect(screen.getByText("Envie materiais de estudo")).toBeInTheDocument();
    expect(screen.getByText("Veja cobertura quando disponível")).toBeInTheDocument();
    expect(screen.getByText("Abra orientação de estudo quando houver edital analisado")).toBeInTheDocument();
    expect(screen.getByText("Questões e avaliações serão liberadas depois")).toBeInTheDocument();
    expect(screen.getByText("Avaliações completas ainda não estão disponíveis.")).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/login");
    expect(screen.getByRole("link", { name: "Enviar edital" })).toHaveAttribute("href", "/materials/upload");
    expect(screen.getByRole("link", { name: "Enviar material" })).toHaveAttribute("href", "/materials/upload");
    expect(screen.getAllByRole("link", { name: "Ver materiais" })[0]).toHaveAttribute("href", "/materials");
    expect(screen.getByRole("link", { name: "Ver editais" })).toHaveAttribute("href", "/editais");
    expect(screen.getAllByRole("link", { name: "Ver referência PSCPP" })[0]).toHaveAttribute("href", "/pscpp");
    expect(screen.getAllByRole("link", { name: "Ver estudo guiado" })[0]).toHaveAttribute("href", "/study");

    expect(screen.getAllByText(/Algumas funções ainda estão em validação/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Pontos de cautela/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/limites de revisão/i)).not.toBeInTheDocument();

    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Processar")).not.toBeInTheDocument();
    expect(screen.queryByText("Reprocessar")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
    expect(screen.queryByText("Agendar")).not.toBeInTheDocument();
    expect(screen.queryByText("Corrigir prova")).not.toBeInTheDocument();
  });

  it("shows an active account step when the user is authenticated", async () => {
    sessionMock.state = {
      status: "authenticated",
      label: "Sessão ativa",
      description: "Você está conectado.",
      source: "backend",
      userLabel: "Smoke Test",
      userId: "user-1"
    };

    render(<OnboardingReadOnlyClient />);

    expect(await screen.findByText("Conta ativa")).toBeInTheDocument();
    expect(screen.getByText("Sua sessão está ativa.")).toBeInTheDocument();
    expect(screen.getByText("Você entrou como Smoke Test.")).toBeInTheDocument();
    expect(screen.queryByText("Sem sessão ativa, as telas evitam tratar exemplos como dados reais.")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Entrar" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Ver painel" })[0]).toHaveAttribute("href", "/dashboard");
  });
});
