"use client";

import { motion } from "framer-motion";

import { DocumentStatusCards } from "@/components/dashboard/DocumentStatusCards";
import { PSCPPProfileCards } from "@/components/dashboard/PSCPPProfileCards";
import { RuntimeStatusCards } from "@/components/dashboard/RuntimeStatusCards";
import { StudyOverviewCards } from "@/components/dashboard/StudyOverviewCards";

export function DashboardPreview() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-12">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.25 }}
        transition={{ duration: 0.5 }}
      >
        <div className="mb-8">
          <div className="section-kicker">preview do produto</div>
          <h2 className="mt-3 font-serif text-4xl text-ink">
            Painel editorial para uma preparação ainda em beta fechado
          </h2>
        </div>
        <div className="naval-window">
          <div className="naval-window-bar">
            <span className="naval-window-dot bg-[#e17d69]" />
            <span className="naval-window-dot bg-[#d6c477]" />
            <span className="naval-window-dot bg-[#8fc9a9]" />
            <div className="window-url">mentorium / visão do painel</div>
          </div>
          <div className="space-y-5 bg-[rgba(10,21,32,0.86)] p-5">
            <StudyOverviewCards />
            <DocumentStatusCards />
            <RuntimeStatusCards />
            <PSCPPProfileCards />
          </div>
        </div>
      </motion.div>
    </section>
  );
}
