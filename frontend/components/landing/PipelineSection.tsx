"use client";

import { motion } from "framer-motion";

import { Card, CardTitle } from "@/components/ui/card";
import { landingPipeline } from "@/lib/mock/mentorium-demo-data";

export function PipelineSection() {
  return (
    <section id="pipeline" className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8">
        <div className="font-mono text-[11px] uppercase tracking-[0.26em] text-silver">
          pipeline
        </div>
        <h2 className="mt-3 font-serif text-4xl text-ink">
          Da base documental ao runtime auditavel
        </h2>
      </div>
      <div className="grid gap-4 lg:grid-cols-7">
        {landingPipeline.map((step, index) => (
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={{ duration: 0.42, delay: index * 0.04 }}
          >
            <Card className="h-full min-h-[168px]">
              <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-gold2">
                etapa {String(index + 1).padStart(2, "0")}
              </div>
              <CardTitle className="mt-6 text-[1.45rem]">{step}</CardTitle>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
