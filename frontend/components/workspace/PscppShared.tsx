"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const pscppNavItems = [
  { href: "/pscpp", label: "Visão geral" },
  { href: "/pscpp/ciclo", label: "Ciclo", status: "Aguardando edital analisado" },
  { href: "/pscpp/questoes", label: "Questões", status: "Em preparação" },
  { href: "/pscpp/mapa", label: "Mapa" }
] as const;

export function PscppSectionNav() {
  const pathname = usePathname();

  return (
    <div className="flex flex-wrap gap-2">
      {pscppNavItems.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`inline-flex items-center rounded-xl border px-4 py-2 text-sm transition ${
              active
                ? "border-[rgba(201,169,110,0.26)] bg-[rgba(201,169,110,0.10)] text-ink"
                : "border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)] text-silver hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
            }`}
          >
            <span>{item.label}</span>
            {"status" in item ? (
              <span className="ml-2 rounded-full border border-[rgba(168,184,196,0.12)] px-2 py-0.5 text-[10px] text-[rgba(232,238,242,0.62)]">
                {item.status}
              </span>
            ) : null}
          </Link>
        );
      })}
    </div>
  );
}
