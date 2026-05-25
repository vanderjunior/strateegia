"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const pscppNavItems = [
  { href: "/pscpp", label: "Workspace" },
  { href: "/pscpp/ciclo", label: "Ciclo" },
  { href: "/pscpp/questoes", label: "Questões" },
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
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}
