import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Mentorium",
  description:
    "Organize edital, materiais de estudo, blocos de leitura e revisão em um caminho guiado."
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
