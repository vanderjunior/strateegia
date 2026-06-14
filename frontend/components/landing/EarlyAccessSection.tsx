import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

export function EarlyAccessSection() {
  return (
    <section id="acesso-antecipado" className="mx-auto max-w-7xl px-6 py-16">
      <Card className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <Badge>preparação guiada</Badge>
          <CardTitle className="mt-6 text-4xl">
            Um caminho de estudo com revisão no centro
          </CardTitle>
          <p className="mt-5 max-w-2xl text-base leading-8 text-silver">
            Use o fluxo atual para organizar edital, materiais e blocos de estudo com cautela.
          </p>
        </div>
        <div className="naval-window">
          <div className="naval-window-bar">
            <span className="naval-window-dot bg-[#e17d69]" />
            <span className="naval-window-dot bg-[#d6c477]" />
            <span className="naval-window-dot bg-[#8fc9a9]" />
            <div className="window-url">preparação guiada</div>
          </div>
          <div className="flex flex-col justify-between gap-6 p-6">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
                estado atual
              </div>
              <ul className="mt-4 space-y-3 text-sm leading-7 text-silver">
                <li>Edital define o escopo da preparação</li>
                <li>Materiais de estudo podem ser preparados</li>
                <li>Blocos orientam o próximo passo</li>
                <li>Revisão acumulada aparece quando houver base suficiente</li>
              </ul>
            </div>
            <div className="flex flex-wrap gap-4">
              <Link href="/onboarding">
                <Button>Solicitar convite</Button>
              </Link>
              <Link href="/materials/upload">
                <Button variant="ghost">Enviar material</Button>
              </Link>
            </div>
          </div>
        </div>
      </Card>
    </section>
  );
}
