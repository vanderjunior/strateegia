"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="mx-auto grid max-w-7xl gap-12 px-6 py-20 lg:grid-cols-[1.15fr_0.85fr] lg:py-28">
      <motion.div
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.65, ease: "easeOut" }}
      >
        <Badge>plataforma edital-aware para estudo tecnico</Badge>
        <h1 className="mt-8 max-w-4xl font-serif text-6xl leading-[0.92] text-ink md:text-7xl">
          Mentorium
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-silver">
          Ambiente em validacao para materiais, editais, bibliografia, questoes,
          simulados, perfis PSCPP/Praticagem e uma cadeia auditavel de
          tentativa, correcao, score e ledger.
        </p>
        <p className="mt-4 max-w-2xl text-base leading-7 text-[rgba(232,238,242,0.68)]">
          Leitura de PDFs textuais ja suportada. OCR permanece experimental e
          sujeito a validacao. A geracao automatica completa de simulado ainda
          nao deve ser tratada como capacidade final verificada.
        </p>
        <div className="mt-10 flex flex-wrap gap-4">
          <Button>Solicitar convite</Button>
          <Link href="/dashboard">
            <Button variant="secondary">Entrar</Button>
          </Link>
        </div>
      </motion.div>
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, delay: 0.08, ease: "easeOut" }}
        className="rounded-[32px] border border-[rgba(201,169,110,0.18)] bg-[linear-gradient(180deg,rgba(21,39,56,0.92),rgba(10,21,32,0.98))] p-6 shadow-shell"
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.26em] text-silver">
              acesso antecipado
            </div>
            <h2 className="mt-3 font-serif text-3xl text-ink">
              Shell premium para um backend ja auditado
            </h2>
          </div>
          <Badge>beta fechado</Badge>
        </div>
        <div className="mt-8 grid gap-4">
          {[
            "pipeline documental bounded",
            "perfis de banca e PSCPP",
            "ciclo flexivel orientado por edital",
            "runtime auditavel de simulado"
          ].map((item) => (
            <div
              key={item}
              className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.02)] px-4 py-4 text-sm uppercase tracking-[0.2em] text-silver"
            >
              {item}
            </div>
          ))}
        </div>
      </motion.div>
    </section>
  );
}
