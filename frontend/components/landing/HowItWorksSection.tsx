import { Card, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { howItWorksSteps } from "@/lib/mock/mentorium-demo-data";

export function HowItWorksSection() {
  return (
    <section id="como-funciona" className="mx-auto max-w-7xl px-6 py-12">
      <div className="mb-8">
        <div className="section-kicker">como funciona</div>
        <h2 className="mt-3 font-serif text-4xl text-ink">
          Produto orientado por evidências, não por slogans
        </h2>
      </div>
      <Card className="overflow-hidden p-0">
        {howItWorksSteps.map((step, index) => (
          <div key={step.id}>
            <div className="grid gap-6 px-6 py-8 md:grid-cols-[96px_1fr]">
              <div className="font-serif text-5xl italic leading-none text-[rgba(232,238,242,0.2)]">
                {step.id}
              </div>
              <div>
                <CardTitle>{step.title}</CardTitle>
                <p className="mt-3 max-w-3xl text-sm leading-7 text-silver">
                  {step.body}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {[
                    index === 0 ? "materiais e edital" : index === 1 ? "mapa PSCPP" : "estudo guiado",
                    index === 0 ? "revisão inicial" : index === 1 ? "gaps encontrados" : "revisão necessária"
                  ].map((chip) => (
                    <span
                      key={chip}
                      className="rounded-full border border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-silver"
                    >
                      {chip}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            {index < howItWorksSteps.length - 1 ? <Separator /> : null}
          </div>
        ))}
      </Card>
    </section>
  );
}
