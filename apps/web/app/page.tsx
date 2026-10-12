import React from "react";
import Link from "next/link";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <DisclaimerBanner />

      <section className="bg-white rounded-2xl p-8 sm:p-12 shadow-sm border border-slate-200 text-center max-w-4xl mx-auto">
        <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight">
          Inteligência Psicométrica <br />
          <span className="text-blue-600">para o seu ENEM</span>
        </h1>
        <p className="mt-4 text-base sm:text-lg text-slate-600 max-w-2xl mx-auto">
          Registre suas respostas e acompanhe estimativas de desempenho quando houver calibração validada para a prova escolhida.
          A correção de redação depende de um provedor de IA configurado.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row justify-center gap-4">
          <Link
            href="/questions"
            className="px-8 py-3.5 bg-white hover:bg-slate-50 text-blue-700 font-semibold rounded-xl transition-all text-sm sm:text-base border border-blue-200"
          >
            Explorar questões TRI
          </Link>
          <Link
            href="/simulator"
            className="px-8 py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-md transition-all text-sm sm:text-base"
          >
            Iniciar Simulado TRI
          </Link>
          <Link
            href="/essay"
            className="px-8 py-3.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold rounded-xl transition-all text-sm sm:text-base border border-slate-300"
          >
            Avaliar Redação com IA
          </Link>
        </div>
      </section>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-2xl mb-2">🎯</div>
          <h3 className="font-bold text-slate-900 text-lg">Modelo 3PL + EAP</h3>
          <p className="text-sm text-slate-600 mt-2">
            O motor calcula proficiência pelo padrão de respostas apenas para itens com parâmetros publicados e vinculados ao caderno.
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-2xl mb-2">📷</div>
          <h3 className="font-bold text-slate-900 text-lg">Cartão por Imagem (OMR)</h3>
          <p className="text-sm text-slate-600 mt-2">
            A API aceita cartão por imagem para confirmação posterior; o envio pela interface ainda está em desenvolvimento.
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-2xl mb-2">✍️</div>
          <h3 className="font-bold text-slate-900 text-lg">Redação 5 Competências</h3>
          <p className="text-sm text-slate-600 mt-2">
            A pré-avaliação pedagógica apresenta as cinco competências e trechos encontrados na redação quando o serviço de IA está disponível.
          </p>
        </div>
      </div>
    </div>
  );
}
