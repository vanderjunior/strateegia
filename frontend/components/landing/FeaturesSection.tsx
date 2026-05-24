import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { landingFeatures } from "@/lib/mock/mentorium-demo-data";

export function FeaturesSection() {
  return (
    <section id="funcionalidades" className="mx-auto max-w-7xl px-6 py-12">
      <div className="mb-8 max-w-3xl">
        <div className="font-mono text-[11px] uppercase tracking-[0.26em] text-silver">
          funcionalidades
        </div>
        <h2 className="mt-3 font-serif text-4xl text-ink">
          Superficie atual do produto, sem promessas alem do que o backend prova
        </h2>
      </div>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {landingFeatures.map((feature) => (
          <Card key={feature.title}>
            <Badge>{feature.badge}</Badge>
            <CardTitle className="mt-5">{feature.title}</CardTitle>
            <p className="mt-4 text-sm leading-7 text-silver">{feature.description}</p>
          </Card>
        ))}
      </div>
    </section>
  );
}
