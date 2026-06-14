"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { MentoriumLogo } from "@/components/brand/MentoriumLogo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function Hero() {
  return (
    <section className="relative mx-auto grid max-w-7xl gap-8 overflow-hidden px-6 py-14 lg:grid-cols-[0.96fr_1.04fr] lg:items-center lg:py-18 xl:gap-10 xl:py-22">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_55%_at_50%_-5%,rgba(201,169,110,0.09)_0%,transparent_65%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_55%_45%_at_15%_80%,rgba(15,30,42,0.7)_0%,transparent_60%),radial-gradient(ellipse_55%_45%_at_85%_80%,rgba(15,30,42,0.5)_0%,transparent_60%)]" />
      <motion.div
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.65, ease: "easeOut" }}
        className="relative z-10 max-w-[38rem]"
      >
        <div className="inline-flex rounded-full border border-[rgba(201,169,110,0.28)] bg-[rgba(201,169,110,0.14)] p-3">
          <MentoriumLogo compact />
        </div>
        <div className="mt-5">
          <Badge>preparação guiada</Badge>
        </div>
        <h1 className="mt-5 max-w-4xl font-serif text-5xl font-light leading-[0.9] tracking-[-0.04em] text-ink md:text-6xl xl:text-[6.4rem]">
          Comece pela <br />
          <em className="font-bold italic text-gold">rota segura.</em>
          <span className="ghost-stroke mt-1 block font-light">Sem pular revisão.</span>
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-8 text-[rgba(232,238,242,0.84)] md:text-[1.05rem]">
          Mentorium organiza edital, materiais de estudo e o próximo bloco de leitura em um caminho claro.
        </p>
        <p className="mt-4 max-w-2xl text-[0.96rem] leading-7 text-[rgba(232,238,242,0.76)]">
          Comece pelo edital, prepare seus materiais e avance com revisão antes das próximas etapas.
        </p>
        <div className="mt-7 flex flex-wrap gap-4">
          <Link href="/onboarding">
            <Button>Comece sua preparação</Button>
          </Link>
          <Link href="/study">
            <Button variant="ghost">Ver estudo de hoje</Button>
          </Link>
        </div>
        <div className="mt-5 flex flex-wrap gap-3 text-sm text-silver">
          <Link href="/materials/upload" className="transition hover:text-ink">
            Enviar material
          </Link>
          <span aria-hidden="true">•</span>
          <Link href="/pscpp/mapa" className="transition hover:text-ink">
            Ver mapa PSCPP
          </Link>
          <span aria-hidden="true">•</span>
          <Link href="/onboarding" className="transition hover:text-ink">
            Solicitar convite
          </Link>
        </div>
      </motion.div>
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, delay: 0.08, ease: "easeOut" }}
        className="naval-window relative z-10 self-center lg:ml-auto lg:w-full lg:max-w-[38rem] xl:max-w-[42rem]"
      >
        <div className="naval-window-bar">
          <span className="naval-window-dot bg-[#e17d69]" />
          <span className="naval-window-dot bg-[#d6c477]" />
          <span className="naval-window-dot bg-[#8fc9a9]" />
          <div className="window-url">mentorium / visão de preparo</div>
        </div>
        <div className="grid min-h-[22rem] lg:grid-cols-[9.5rem_minmax(0,1fr)] xl:min-h-[24rem]">
          <div className="border-r border-[rgba(168,184,196,0.1)] bg-[rgba(10,21,32,0.94)] p-4">
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-[rgba(168,184,196,0.52)]">
              jornada
            </div>
            <div className="mt-5 space-y-2">
              {["Começar", "Materiais", "Editais", "Mapa PSCPP", "Estudo", "Próximas etapas"].map((item, index) => (
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
          <div className="min-w-0 space-y-4 bg-[rgba(26,47,63,0.78)] p-4 lg:p-5">
            <div className="grid grid-cols-1 gap-3.5 min-[980px]:grid-cols-[repeat(3,minmax(0,1fr))]">
              {[
                { label: "MATERIAIS", value: "PDF e texto", note: "Preparar" },
                { label: "EDITAL", value: "Escopo", note: "Analisar" },
                { label: "ESTUDO", value: "Blocos", note: "Continuar" }
              ].map((item) => (
                <div key={item.label} className="min-w-0 rounded-2xl border border-[rgba(168,184,196,0.1)] bg-[rgba(21,39,56,0.76)] px-3.5 py-3.5 lg:px-4 lg:py-4">
                  <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-[rgba(168,184,196,0.54)]">
                    {item.label}
                  </div>
                  <div className="mt-2 whitespace-normal text-[1.1rem] font-medium leading-tight tracking-[-0.02em] text-ink sm:text-[1.22rem] lg:text-[1.32rem]">
                    {item.value}
                  </div>
                  <div className="mt-2 whitespace-normal text-[11px] uppercase tracking-[0.14em] text-gold2 lg:text-[0.8rem]">
                    {item.note}
                  </div>
                </div>
              ))}
            </div>
            <div className="rounded-[24px] border border-[rgba(168,184,196,0.1)] bg-[rgba(10,21,32,0.72)] p-4">
              <div className="section-kicker">caminho de preparação</div>
              <div className="mt-5 space-y-4">
                {[
                  { label: "Enviar material", fill: "88%", tone: "ok" },
                  { label: "Revisar edital", fill: "76%", tone: "ok" },
                  { label: "Mapa PSCPP", fill: "82%", tone: "ok" },
                  { label: "Revisão acumulada", fill: "38%", tone: "warn" }
                ].map((item) => (
                  <div key={item.label} className="flex min-w-0 items-center gap-3 border-b border-[rgba(168,184,196,0.08)] pb-3 last:border-b-0 last:pb-0">
                    <span className="flex-1 text-sm leading-6 text-silver">{item.label}</span>
                    <div className="h-[2px] w-20 shrink-0 overflow-hidden rounded-full bg-[rgba(255,255,255,0.07)] lg:w-24">
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
