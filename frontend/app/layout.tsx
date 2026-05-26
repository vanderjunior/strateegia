import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Mentorium",
  description:
    "Plataforma em beta fechado para materiais, edital, mapa PSCPP e estudo guiado com revisão necessária."
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
