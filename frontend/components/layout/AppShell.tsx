import type { PropsWithChildren } from "react";

import { MentoriumLogo } from "@/components/brand/MentoriumLogo";
import { Badge } from "@/components/ui/badge";
import { dashboardSidebar } from "@/lib/mock/mentorium-demo-data";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen bg-[var(--color-s3)] text-ink">
      <div className="grid min-h-screen lg:grid-cols-[280px_1fr]">
        <aside className="border-r border-[rgba(168,184,196,0.10)] bg-[rgba(10,21,32,0.9)] px-6 py-8">
          <MentoriumLogo compact />
          <div className="mt-6 space-y-3">
            <Badge>acesso antecipado</Badge>
            <p className="max-w-[220px] text-sm leading-6 text-silver">
              Shell de produto em modo experimental, refletindo apenas capacidades auditadas do backend.
            </p>
          </div>
          <nav className="mt-10 space-y-2">
            {dashboardSidebar.map((item, index) => (
              <div
                key={item}
                className={`rounded-2xl border px-4 py-3 text-sm ${
                  index === 0
                    ? "border-[rgba(201,169,110,0.26)] bg-[rgba(201,169,110,0.10)] text-ink"
                    : "border-transparent text-silver"
                }`}
              >
                {item}
              </div>
            ))}
          </nav>
        </aside>
        <div className="bg-radial-shell">
          <header className="flex items-center justify-between border-b border-[rgba(168,184,196,0.08)] px-6 py-5 lg:px-10">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
                mentorium / dashboard
              </div>
              <h1 className="mt-2 font-serif text-3xl text-ink">Painel de capacidades auditadas</h1>
            </div>
            <Badge>mock state</Badge>
          </header>
          <main className="px-6 py-8 lg:px-10">{children}</main>
        </div>
      </div>
    </div>
  );
}
