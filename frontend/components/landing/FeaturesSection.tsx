import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { landingFeatures } from "@/lib/mock/mentorium-demo-data";

export function FeaturesSection() {
  return (
    <section id="funcionalidades" className="mx-auto max-w-7xl px-6 py-12">
      <div className="mb-8 max-w-3xl">
        <div className="section-kicker">funcionalidades</div>
        <h2 className="mt-3 font-serif text-4xl text-ink">
          Superficie atual do produto, sem promessas alem do que o backend prova
        </h2>
      </div>
      <div className="grid gap-px overflow-hidden rounded-[30px] border border-[rgba(168,184,196,0.1)] bg-[rgba(168,184,196,0.1)] md:grid-cols-2 xl:grid-cols-3">
        {landingFeatures.map((feature) => (
          <Card key={feature.title} className="rounded-none border-0 shadow-none">
            <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-[rgba(10,21,32,0.9)] text-lg">
              {feature.title.startsWith("PDF") ? "◫" : feature.title.startsWith("Editais") ? "§" : feature.title.startsWith("Perfil") ? "✦" : feature.title.startsWith("Ciclo") ? "↻" : feature.title.startsWith("Runtime") ? "⟐" : "◌"}
            </div>
            <Badge>{feature.badge}</Badge>
            <CardTitle className="mt-5">{feature.title}</CardTitle>
            <p className="mt-4 text-sm leading-7 text-silver">{feature.description}</p>
          </Card>
        ))}
      </div>
    </section>
  );
}
