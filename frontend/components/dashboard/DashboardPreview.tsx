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
          <div className="font-mono text-[11px] uppercase tracking-[0.26em] text-silver">
            preview do produto
          </div>
          <h2 className="mt-3 font-serif text-4xl text-ink">
            Shell editorial para uma operacao ainda em beta fechado
          </h2>
        </div>
        <div className="space-y-5 rounded-[36px] border border-[rgba(201,169,110,0.18)] bg-[rgba(10,21,32,0.86)] p-5 shadow-shell">
          <StudyOverviewCards />
          <DocumentStatusCards />
          <RuntimeStatusCards />
          <PSCPPProfileCards />
        </div>
      </motion.div>
    </section>
  );
}
