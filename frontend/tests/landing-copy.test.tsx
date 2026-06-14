import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EarlyAccessSection } from "@/components/landing/EarlyAccessSection";
import { Hero } from "@/components/landing/Hero";
import { PublicNav } from "@/components/layout/PublicNav";

describe("landing copy and CTA safety", () => {
  it("keeps the landing aligned with onboarding, study, and early-access language", () => {
    render(
      <div>
        <PublicNav />
        <Hero />
        <EarlyAccessSection />
      </div>
    );

    expect(screen.getAllByText("Comece sua preparação").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Ver estudo de hoje" })).toHaveAttribute("href", "/study");
    expect(screen.getAllByRole("link", { name: "Solicitar convite" })[0]).toHaveAttribute("href", "/onboarding");
    expect(screen.getAllByRole("link", { name: "Enviar material" })[0]).toHaveAttribute("href", "/materials/upload");
    expect(screen.getAllByText(/preparação guiada/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Revisão acumulada/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Materiais de estudo/i).length).toBeGreaterThan(0);

    expect(screen.queryByText(/comprar/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/assinatura/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/checkout/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/gerar simulado/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/aplicar progresso/i)).not.toBeInTheDocument();
  });
});
