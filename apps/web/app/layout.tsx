import React from "react";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

export const metadata = {
  title: "ENEM Intelligence - Estimador Psicométrico TRI e Redação",
  description: "Plataforma independente de estimativa de notas do ENEM com 3PL, EAP e validação em microdados.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
        <footer className="bg-slate-900 text-slate-400 py-6 text-center text-xs border-t border-slate-800">
          <p>© 2026 ENEM Intelligence. Plataforma independente e não oficial do INEP.</p>
          <p className="mt-1">
            Conforme a LGPD (Lei nº 13.709/2018), imagens de cartões possuem retenção temporária e dados são tratados estritamente para estimativa educacional.
          </p>
        </footer>
      </body>
    </html>
  );
}
