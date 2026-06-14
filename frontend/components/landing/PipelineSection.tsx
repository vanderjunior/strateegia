"use client";

import { motion } from "framer-motion";

import { Card, CardTitle } from "@/components/ui/card";
import { landingPipeline } from "@/lib/mock/mentorium-demo-data";

export function PipelineSection() {
  return (
    <section id="pipeline" className="mx-auto max-w-7xl px-6 py-14">
      <div className="mb-8 max-w-3xl">
        <div className="section-kicker">caminho seguro</div>
        <h2 className="mt-3 font-serif text-4xl text-ink">
          De materiais e edital ao estudo guiado
        </h2>
        <p className="mt-4 text-base leading-8 text-silver">
          Siga uma sequência simples: envie materiais, analise o edital, prepare o conteúdo e estude por blocos.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {landingPipeline.map((step, index) => (
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 16 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={{ duration: 0.42, delay: index * 0.04 }}
          >
            <Card className="h-full min-h-[148px]">
              <div className="flex gap-4">
                <div className="flex w-8 flex-col items-center">
                  <div className={`mt-1 h-3 w-3 rounded-full border ${index === 4 ? "border-gold bg-gold shadow-[0_0_0_4px_rgba(201,169,110,0.14)]" : "border-[rgba(168,184,196,0.18)] bg-[rgba(10,21,32,0.9)]"}`} />
                  {index < landingPipeline.length - 1 ? (
                    <div className="mt-2 h-full min-h-16 w-px bg-[linear-gradient(180deg,rgba(168,184,196,0.18),transparent)]" />
                  ) : null}
                </div>
                <div className="flex-1">
                  <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-gold2">
                    etapa {String(index + 1).padStart(2, "0")}
                  </div>
                  <CardTitle className="mt-4 text-[1.6rem]">{step}</CardTitle>
                  <p className="mt-3 text-sm leading-7 text-silver">
                    {index < 4
                      ? "Leitura e conferência antes de avançar para o próximo bloco."
                      : index < 6
                        ? "Organização por perfil, edital e pontos que merecem revisão."
                        : "Etapa futura sem alteração automática neste momento."}
                  </p>
                </div>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
