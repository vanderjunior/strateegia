import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

export function EarlyAccessSection() {
  return (
    <section id="acesso-antecipado" className="mx-auto max-w-7xl px-6 py-16">
      <Card className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <Badge>acesso antecipado</Badge>
          <CardTitle className="mt-6 text-4xl">
            Beta fechado para uma plataforma ainda em validação
          </CardTitle>
          <p className="mt-5 max-w-2xl text-base leading-8 text-silver">
            Mentorium não está se apresentando como produto público pronto. O objetivo desta fase é
            validar materiais, edital, mapa PSCPP e estudo guiado antes de qualquer abertura ampla.
          </p>
        </div>
        <div className="naval-window">
          <div className="naval-window-bar">
            <span className="naval-window-dot bg-[#e17d69]" />
            <span className="naval-window-dot bg-[#d6c477]" />
            <span className="naval-window-dot bg-[#8fc9a9]" />
            <div className="window-url">beta fechado / acesso por convite</div>
          </div>
          <div className="flex flex-col justify-between gap-6 p-6">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
                estado atual
              </div>
              <ul className="mt-4 space-y-3 text-sm leading-7 text-silver">
                <li>Leitura de PDFs textuais suportada</li>
                <li>OCR em validação para arquivos escaneados</li>
                <li>Mapa PSCPP e ciclo sugerido já disponíveis</li>
                <li>Simulado em preparação e revisão necessária</li>
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
