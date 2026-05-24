import { Card, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { howItWorksSteps } from "@/lib/mock/mentorium-demo-data";

export function HowItWorksSection() {
  return (
    <section id="como-funciona" className="mx-auto max-w-7xl px-6 py-12">
      <div className="mb-8">
        <div className="font-mono text-[11px] uppercase tracking-[0.26em] text-silver">
          como funciona
        </div>
        <h2 className="mt-3 font-serif text-4xl text-ink">
          Produto orientado por evidencias, nao por slogans
        </h2>
      </div>
      <Card className="overflow-hidden p-0">
        {howItWorksSteps.map((step, index) => (
          <div key={step.id}>
            <div className="grid gap-6 px-6 py-6 md:grid-cols-[120px_1fr]">
              <div className="font-mono text-sm uppercase tracking-[0.28em] text-gold2">
                {step.id}
              </div>
              <div>
                <CardTitle>{step.title}</CardTitle>
                <p className="mt-3 max-w-3xl text-sm leading-7 text-silver">
                  {step.body}
                </p>
              </div>
            </div>
            {index < howItWorksSteps.length - 1 ? <Separator /> : null}
          </div>
        ))}
      </Card>
    </section>
  );
}
