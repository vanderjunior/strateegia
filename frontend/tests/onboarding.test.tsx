import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OnboardingReadOnlyClient } from "@/components/workspace/OnboardingReadOnlyClient";

describe("OnboardingReadOnlyClient", () => {
  it("renders the first-use path with safe links and no mutation CTAs", () => {
    render(<OnboardingReadOnlyClient />);

    expect(screen.getByText("Comece sua preparação")).toBeInTheDocument();
    expect(screen.getByText("Envie material")).toBeInTheDocument();
    expect(screen.getByText("Revise edital")).toBeInTheDocument();
    expect(screen.getByText("Veja o mapa PSCPP")).toBeInTheDocument();
    expect(screen.getByText("Siga o estudo de hoje")).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "Enviar material" })).toHaveAttribute("href", "/materials/upload");
    expect(screen.getAllByRole("link", { name: "Ver materiais" })[0]).toHaveAttribute("href", "/materials");
    expect(screen.getByRole("link", { name: "Ver editais" })).toHaveAttribute("href", "/editais");
    expect(screen.getAllByRole("link", { name: "Ver mapa PSCPP" })[0]).toHaveAttribute("href", "/pscpp/mapa");
    expect(screen.getAllByRole("link", { name: "Ver ciclo PSCPP" })[0]).toHaveAttribute("href", "/pscpp/ciclo");
    expect(screen.getAllByRole("link", { name: "Ver estudo de hoje" })[0]).toHaveAttribute("href", "/study");

    expect(screen.getAllByText(/OCR em validação/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Análise candidata").length).toBeGreaterThan(0);
    expect(screen.getByText(/Não altera seu progresso/i)).toBeInTheDocument();

    expect(screen.queryByText("Gerar questões")).not.toBeInTheDocument();
    expect(screen.queryByText("Gerar simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Processar")).not.toBeInTheDocument();
    expect(screen.queryByText("Reprocessar")).not.toBeInTheDocument();
    expect(screen.queryByText("Aplicar progresso")).not.toBeInTheDocument();
    expect(screen.queryByText("Agendar")).not.toBeInTheDocument();
    expect(screen.queryByText("Corrigir prova")).not.toBeInTheDocument();
  });
});
