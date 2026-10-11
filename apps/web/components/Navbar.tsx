import React from "react";
import Link from "next/link";

export function Navbar() {
  return (
    <header className="bg-slate-900 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center space-x-3">
          <span className="text-xl font-extrabold tracking-tight text-blue-400">
            ENEM TRI <span className="text-white text-sm font-medium px-2 py-0.5 bg-blue-600 rounded">Intelligence</span>
          </span>
        </div>
        <nav className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-medium" aria-label="Navegação principal">
          <Link href="/" className="hover:text-blue-400 transition-colors">
            Início
          </Link>
          <Link href="/simulator" className="hover:text-blue-400 transition-colors">
            Simulador TRI
          </Link>
          <Link href="/essay" className="hover:text-blue-400 transition-colors">
            Redação IA
          </Link>
          <Link href="/history" className="hover:text-blue-400 transition-colors">
            Histórico & Evolução
          </Link>
          <Link href="/login" className="hover:text-blue-400 transition-colors">
            Entrar
          </Link>
        </nav>
      </div>
    </header>
  );
}
