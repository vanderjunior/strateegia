"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { MentoriumLogo } from "@/components/brand/MentoriumLogo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="relative mx-auto grid max-w-7xl gap-12 overflow-hidden px-6 py-20 lg:grid-cols-[1.06fr_0.94fr] lg:py-28">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_55%_at_50%_-5%,rgba(201,169,110,0.09)_0%,transparent_65%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_55%_45%_at_15%_80%,rgba(15,30,42,0.7)_0%,transparent_60%),radial-gradient(ellipse_55%_45%_at_85%_80%,rgba(15,30,42,0.5)_0%,transparent_60%)]" />
      <motion.div
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.65, ease: "easeOut" }}
        className="relative z-10"
      >
        <div className="inline-flex rounded-full border border-[rgba(201,169,110,0.28)] bg-[rgba(201,169,110,0.14)] p-3">
          <MentoriumLogo compact />
        </div>
        <div className="mt-8">
          <Badge>plataforma edital-aware para estudo tecnico</Badge>
        </div>
        <h1 className="mt-8 max-w-5xl font-serif text-6xl font-light leading-[0.92] tracking-[-0.04em] text-ink md:text-7xl xl:text-[7rem]">
          Estude o que <br />
          <em className="font-bold italic text-gold">vai cair.</em>
          <span className="ghost-stroke block font-light">Nada alem.</span>
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-[rgba(232,238,242,0.75)]">
          Ambiente em validacao para materiais, editais, bibliografia, questoes, simulados, perfil PSCPP/Praticagem e uma cadeia auditavel de tentativa, correcao, score e ledger.
        </p>
        <p className="mt-4 max-w-2xl text-base leading-7 text-[rgba(232,238,242,0.68)]">
          Leitura de PDFs textuais ja suportada. OCR permanece experimental e sujeito a validacao. A geracao automatica completa de simulado ainda nao deve ser tratada como capacidade final verificada.
        </p>
        <div className="mt-10 flex flex-wrap gap-4">
          <Button>Solicitar convite</Button>
          <Link href="/dashboard">
            <Button variant="ghost">Entrar</Button>
          </Link>
        </div>
      </motion.div>
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, delay: 0.08, ease: "easeOut" }}
        className="naval-window relative z-10"
      >
        <div className="naval-window-bar">
          <span className="naval-window-dot bg-[#e17d69]" />
          <span className="naval-window-dot bg-[#d6c477]" />
          <span className="naval-window-dot bg-[#8fc9a9]" />
          <div className="window-url">mentorium / preview read-only</div>
        </div>
        <div className="grid min-h-[27rem] lg:grid-cols-[11rem_1fr]">
          <div className="border-r border-[rgba(168,184,196,0.1)] bg-[rgba(10,21,32,0.94)] p-4">
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-[rgba(168,184,196,0.52)]">
              shell
            </div>
            <div className="mt-5 space-y-2">
              {["Dashboard", "Materiais", "Editais", "Ciclo", "PSCPP", "Runtime"].map((item, index) => (
                <div
                  key={item}
                  className={`rounded-xl px-3 py-2 text-sm ${
                    index === 0
                      ? "glass-gold text-gold2"
                      : "text-[rgba(232,238,242,0.58)]"
                  }`}
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-4 bg-[rgba(26,47,63,0.78)] p-5">
            <div className="grid gap-3 md:grid-cols-3">
              {[
                { label: "documentos", value: "PDF textual", note: "suportado" },
                { label: "OCR", value: "experimental", note: "validacao" },
                { label: "runtime", value: "auditavel", note: "testado" }
              ].map((item) => (
                <div key={item.label} className="rounded-2xl border border-[rgba(168,184,196,0.1)] bg-[rgba(21,39,56,0.76)] p-4">
                  <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-[rgba(168,184,196,0.48)]">
                    {item.label}
                  </div>
                  <div className="mt-3 font-serif text-3xl text-ink">{item.value}</div>
                  <div className="mt-2 text-sm text-gold2">{item.note}</div>
                </div>
              ))}
            </div>
            <div className="rounded-[24px] border border-[rgba(168,184,196,0.1)] bg-[rgba(10,21,32,0.72)] p-4">
              <div className="section-kicker">pipeline auditado</div>
              <div className="mt-5 space-y-4">
                {[
                  { label: "Leitura documental", fill: "88%", tone: "ok" },
                  { label: "Perfil PSCPP", fill: "92%", tone: "ok" },
                  { label: "Ciclo flexivel", fill: "74%", tone: "ok" },
                  { label: "Simulado completo", fill: "38%", tone: "warn" }
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-3 border-b border-[rgba(168,184,196,0.08)] pb-3 last:border-b-0 last:pb-0">
                    <span className="flex-1 text-sm text-silver">{item.label}</span>
                    <div className="h-[2px] w-24 overflow-hidden rounded-full bg-[rgba(255,255,255,0.07)]">
                      <div
                        className={`h-full rounded-full ${item.tone === "warn" ? "bg-gradient-to-r from-[#c87862] to-[#dfc08a]" : "bg-gradient-to-r from-silver to-ink"}`}
                        style={{ width: item.fill }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
