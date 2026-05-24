import { DocumentStatusCards } from "@/components/dashboard/DocumentStatusCards";
import { PSCPPProfileCards } from "@/components/dashboard/PSCPPProfileCards";
import { RuntimeStatusCards } from "@/components/dashboard/RuntimeStatusCards";
import { StudyOverviewCards } from "@/components/dashboard/StudyOverviewCards";
import { Badge } from "@/components/ui/badge";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-[32px] border border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)] p-6">
          <Badge>beta fechado</Badge>
          <h2 className="mt-5 font-serif text-4xl text-ink">
            Estado atual do produto, sem esconder o que ainda esta em validacao
          </h2>
          <p className="mt-4 max-w-3xl text-sm leading-8 text-silver">
            Este dashboard usa apenas mock state. Ele reflete as capacidades
            auditadas do backend: leitura de PDFs textuais, OCR experimental,
            ingestao parcial de edital, alinhamento parcial de bibliografia,
            perfis PSCPP implementados e cadeia auditavel de simulado.
          </p>
        </div>
        <div className="rounded-[32px] border border-[rgba(168,184,196,0.10)] bg-[rgba(10,21,32,0.76)] p-6">
          <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
            restricoes claras
          </div>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            <li>Sem mutacao real de scheduler ou calendario</li>
            <li>Sem overclaim de OCR para PDF escaneado</li>
            <li>Sem promessa de simulado completo automatico ja validado</li>
            <li>Sem exposicao de answer key ou gabarito</li>
          </ul>
        </div>
      </section>

      <StudyOverviewCards />

      <section className="space-y-4">
        <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
          materiais e edital
        </div>
        <DocumentStatusCards />
      </section>

      <section className="space-y-4">
        <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
          perfis PSCPP
        </div>
        <PSCPPProfileCards />
      </section>

      <section className="space-y-4">
        <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
          runtime e ledger
        </div>
        <RuntimeStatusCards />
      </section>
    </div>
  );
}
