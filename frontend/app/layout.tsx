import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Mentorium",
  description:
    "Plataforma edital-aware em beta fechado para estudo tecnico, perfis PSCPP e runtime auditavel de simulado."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
