"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";

type Area = {
  area: string;
  raw_correct: number;
  total_items: number;
  percentage: number;
  estimated_score?: number | null;
  theta_eap?: number | null;
  interval_95?: [number, number] | null;
};

type ItemDetail = {
  position: number;
  area: string;
  selected_answer: string | null;
  official_key: string;
  is_correct: boolean | null;
  annulled: boolean;
};

type Summary = {
  attempt_id: string;
  exam_title: string;
  year: number;
  day: number;
  booklet_color: string;
  booklet_description: string;
  status: string;
  has_tri_calibration: boolean;
  total_correct: number;
  total_items: number;
  areas: Area[];
  items: ItemDetail[];
  disclaimer: string;
};

export default function ResultPage() {
  const params = useParams();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [filterArea, setFilterArea] = useState<string>("ALL");

  useEffect(() => {
    api<Summary>(`/attempts/${params.id}/summary`)
      .then(setSummary)
      .catch((caught) => setError(caught.message));
  }, [params.id]);

  const displayedItems = summary
    ? filterArea === "ALL"
      ? summary.items
      : summary.items.filter((it) => it.area === filterArea)
    : [];

  return (
    <main className="mx-auto max-w-5xl space-y-6">
      <DisclaimerBanner />

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Resultado do Simulado</h1>
            {summary && (
              <p className="mt-1 text-sm text-slate-600">
                {summary.exam_title} · {summary.booklet_description}
              </p>
            )}
          </div>
          {summary && (
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                summary.has_tri_calibration
                  ? "bg-purple-100 text-purple-800 border border-purple-200"
                  : "bg-blue-100 text-blue-800 border border-blue-200"
              }`}
            >
              {summary.has_tri_calibration ? "✨ Estimativa TRI + Gabarito" : "📝 Gabarito Oficial Inep"}
            </span>
          )}
        </div>

        {!summary && !error && (
          <p role="status" className="mt-6 text-sm text-slate-500">
            Carregando resultado...
          </p>
        )}
        {error && (
          <p role="alert" className="mt-6 rounded-lg bg-red-50 p-3 text-sm text-red-800">
            {error}
          </p>
        )}

        {summary && (
          <>
            {/* Banner de resumo geral */}
            <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 p-5">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Total de Acertos</p>
                <p className="mt-1 text-3xl font-extrabold text-slate-900">
                  {summary.total_correct}{" "}
                  <span className="text-base font-normal text-slate-500">/ {summary.total_items} questões</span>
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Aproveitamento Geral</p>
                <p className="mt-1 text-3xl font-extrabold text-blue-700">
                  {((summary.total_correct / (summary.total_items || 1)) * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            {/* Cards por Área */}
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {summary.areas.map((area) => (
                <article
                  key={area.area}
                  className="relative rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:border-slate-300"
                >
                  <div className="flex items-center justify-between">
                    <h2 className="text-base font-bold text-slate-900">
                      Área {area.area}{" "}
                      <span className="text-xs font-normal text-slate-500">
                        {area.area === "LC"
                          ? "(Linguagens e Códigos)"
                          : area.area === "CH"
                          ? "(Ciências Humanas)"
                          : area.area === "CN"
                          ? "(Ciências da Natureza)"
                          : "(Matemática)"}
                      </span>
                    </h2>
                    <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                      {area.percentage}% de acerto
                    </span>
                  </div>

                  {area.estimated_score ? (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-slate-500">Nota TRI estimada (não oficial)</p>
                      <p className="text-4xl font-extrabold text-purple-700">{area.estimated_score.toFixed(1)}</p>
                      {area.interval_95 && (
                        <p className="mt-1 text-xs text-slate-500">
                          Intervalo 95%: {area.interval_95[0].toFixed(1)} a {area.interval_95[1].toFixed(1)}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="mt-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                      Gabarito conferido contra a prova oficial do Inep.
                    </div>
                  )}

                  <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-sm text-slate-700">
                    <span>Acertos brutos:</span>
                    <span className="font-bold text-slate-900">
                      {area.raw_correct} / {area.total_items}
                    </span>
                  </div>
                </article>
              ))}
            </div>

            {/* Gabarito Detalhado Questão por Questão */}
            <div className="mt-8">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
                <h3 className="text-lg font-bold text-slate-900">Conferência Questão por Questão</h3>
                <div className="flex gap-1 text-xs">
                  <button
                    onClick={() => setFilterArea("ALL")}
                    className={`rounded-lg px-2.5 py-1 font-medium ${
                      filterArea === "ALL" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    Todas ({summary.items.length})
                  </button>
                  {summary.areas.map((a) => (
                    <button
                      key={a.area}
                      onClick={() => setFilterArea(a.area)}
                      className={`rounded-lg px-2.5 py-1 font-medium ${
                        filterArea === a.area
                          ? "bg-slate-900 text-white"
                          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                      }`}
                    >
                      {a.area} ({a.total_items})
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-9">
                {displayedItems.map((it) => {
                  const isCorrect = it.is_correct === true;
                  const isWrong = it.is_correct === false;
                  const isAnnulled = it.annulled;
                  return (
                    <div
                      key={it.position}
                      className={`flex flex-col items-center justify-center rounded-lg border p-2 text-center text-xs ${
                        isAnnulled
                          ? "border-amber-300 bg-amber-50 text-amber-900"
                          : isCorrect
                          ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                          : isWrong
                          ? "border-red-200 bg-red-50 text-red-900"
                          : "border-slate-200 bg-slate-50 text-slate-600"
                      }`}
                    >
                      <span className="font-bold">Q{it.position}</span>
                      <div className="mt-1 flex items-center gap-1">
                        {isAnnulled ? (
                          <span className="font-semibold text-amber-700">Anulada</span>
                        ) : isCorrect ? (
                          <span className="font-extrabold text-emerald-600">✓ {it.official_key}</span>
                        ) : (
                          <>
                            <span className="text-red-500 font-semibold line-through">
                              {it.selected_answer || "—"}
                            </span>
                            <span className="font-bold text-slate-700">({it.official_key})</span>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <p className="mt-6 text-xs text-slate-500">{summary.disclaimer}</p>
          </>
        )}

        <div className="mt-8 flex flex-wrap gap-3 border-t border-slate-200 pt-5">
          <Link
            href="/simulator"
            className="rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-800"
          >
            Novo Simulado
          </Link>
          <Link
            href="/history"
            className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
          >
            Ver Meu Histórico
          </Link>
        </div>
      </section>
    </main>
  );
}
