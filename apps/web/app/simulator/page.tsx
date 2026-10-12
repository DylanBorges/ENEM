"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, token } from "@/lib/api";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";

type Exam = { id: string; year: number; application: string; title: string; has_calibration?: boolean };
type Booklet = { id: string; day: number; color: string; language: string | null; description: string; paper_url: string | null; pdf_download_url?: string | null };
type Item = { physical_position: number; area: string; annulled: boolean };
const choices = ["A", "B", "C", "D", "E"];

export default function SimulatorPage() {
  const router = useRouter();
  const [exams, setExams] = useState<Exam[]>([]);
  const [examId, setExamId] = useState("");
  const [booklets, setBooklets] = useState<Booklet[]>([]);
  const [bookletId, setBookletId] = useState("");
  const [items, setItems] = useState<Item[]>([]);

  // Modo: "check" (apenas marcar as que acertou) ou "letters" (A-E)
  const [inputMode, setInputMode] = useState<"check" | "letters">("check");

  // Armazenamento para modo check (Set de posições acertadas)
  const [checkedPositions, setCheckedPositions] = useState<Set<number>>(new Set());

  // Armazenamento para modo tradicional A-E
  const [answers, setAnswers] = useState<Record<number, string>>({});

  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [demoLoginLoading, setDemoLoginLoading] = useState(false);

  const selectedBooklet = booklets.find((b) => b.id === bookletId);
  const validItems = items.filter((item) => !item.annulled);

  useEffect(() => {
    setSignedIn(Boolean(token()));
    api<Exam[]>("/exams?all=true")
      .then((data) => {
        setExams(data);
        if (data.length > 0) {
          setExamId(data[0].id);
        }
      })
      .catch((caught) => setError(caught.message));
  }, []);

  useEffect(() => {
    setBooklets([]);
    setBookletId("");
    setItems([]);
    setCheckedPositions(new Set());
    setAnswers({});
    if (examId) {
      api<Booklet[]>(`/exams/${examId}/booklets`)
        .then((data) => {
          setBooklets(data);
          if (data.length > 0) {
            setBookletId(data[0].id);
          }
        })
        .catch((caught) => setError(caught.message));
    }
  }, [examId]);

  useEffect(() => {
    setItems([]);
    setCheckedPositions(new Set());
    setAnswers({});
    if (bookletId) {
      api<Item[]>(`/exams/booklets/${bookletId}/items`)
        .then(setItems)
        .catch((caught) => setError(caught.message));
    }
  }, [bookletId]);

  // Função para alternar check de uma questão
  function toggleCheck(pos: number) {
    setCheckedPositions((prev) => {
      const next = new Set(prev);
      if (next.has(pos)) {
        next.delete(pos);
      } else {
        next.add(pos);
      }
      return next;
    });
  }

  function selectAll() {
    const all = new Set<number>();
    validItems.forEach((it) => all.add(it.physical_position));
    setCheckedPositions(all);
  }

  function clearAll() {
    setCheckedPositions(new Set());
  }

  async function quickDemoLogin() {
    setDemoLoginLoading(true);
    setError("");
    try {
      const result = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "estudante@enem.com", password: "Senha@123" }),
      });
      sessionStorage.setItem("access_token", result.access_token);
      setSignedIn(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha no login demo");
    } finally {
      setDemoLoginLoading(false);
    }
  }

  async function score() {
    setError("");
    setBusy(true);
    try {
      const attempt = await api<{ id: string }>("/attempts", {
        method: "POST",
        body: JSON.stringify({ booklet_id: bookletId }),
      });

      let responsesPayload: Array<{ position: number; answer?: string; is_correct?: boolean }>;

      if (inputMode === "check") {
        // Envia todas as questões válidas: marcadas como certas (true), desmarcadas como erradas (false)
        responsesPayload = validItems.map((item) => ({
          position: item.physical_position,
          is_correct: checkedPositions.has(item.physical_position),
        }));
      } else {
        responsesPayload = Object.entries(answers).map(([position, answer]) => ({
          position: Number(position),
          answer,
        }));
      }

      await api(`/attempts/${attempt.id}/responses`, {
        method: "PUT",
        body: JSON.stringify({ responses: responsesPayload }),
      });

      const currentExam = exams.find((e) => e.id === examId);
      if (currentExam?.has_calibration) {
        try {
          await api(`/attempts/${attempt.id}/score`, { method: "POST" });
        } catch (scoreErr) {
          console.warn("Calibração TRI não aplicada:", scoreErr);
        }
      }
      router.push(`/result/${attempt.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao calcular estimativa");
    } finally {
      setBusy(false);
    }
  }

  const correctCount = checkedPositions.size;
  const totalCount = validItems.length;

  return (
    <main className="mx-auto max-w-5xl space-y-6">
      <DisclaimerBanner />

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <h1 className="text-2xl font-bold text-slate-900">Simulador de Nota TRI ENEM</h1>
        <p className="mt-2 text-sm text-slate-600">
          Calcule sua proficiência e nota estimadas com o modelo 3PL e estimador EAP. O resultado não é oficial.
        </p>

        {!signedIn && (
          <div className="mt-4 flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-amber-900">
              Você não está conectado. Entre para registrar suas tentativas e visualizar a evolução.
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={quickDemoLogin}
                disabled={demoLoginLoading}
                className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-amber-700 disabled:opacity-50"
              >
                {demoLoginLoading ? "Conectando..." : "Entrar como Estudante (1 clique)"}
              </button>
              <Link
                href="/login"
                className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-100"
              >
                Login / Cadastro
              </Link>
            </div>
          </div>
        )}

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-semibold text-slate-800">
            Edição e aplicação
            <select
              value={examId}
              onChange={(e) => setExamId(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-3 font-normal text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">Selecione o Exame</option>
              {exams.map((exam) => (
                <option key={exam.id} value={exam.id}>
                  {exam.title} {exam.has_calibration ? "✨ [TRI + Gabarito]" : "📝 [Gabarito Oficial]"}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm font-semibold text-slate-800">
            Caderno de Prova
            <select
              value={bookletId}
              onChange={(e) => setBookletId(e.target.value)}
              disabled={!examId}
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-3 font-normal text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
            >
              <option value="">Selecione o Caderno</option>
              {booklets.map((b) => (
                <option key={b.id} value={b.id}>
                  Dia {b.day} · {b.color} {b.language ? `· ${b.language}` : ""}
                </option>
              ))}
            </select>
          </label>
        </div>

        {selectedBooklet?.paper_url && (
          <div className="mt-5 flex flex-col gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="font-medium">Caderno oficial do Inep disponível em PDF</p>
              <p className="text-xs text-blue-800">Você pode consultar o caderno completo de questões para estudar e conferir o gabarito.</p>
            </div>
            <a
              href={selectedBooklet.paper_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-h-11 w-full shrink-0 items-center justify-center rounded-lg bg-blue-700 px-3.5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 sm:w-auto"
            >
              Abrir Caderno PDF ↗
            </a>
          </div>
        )}

        {exams.length === 0 && !error && (
          <p className="mt-5 rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
            Carregando provas disponíveis... Na hospedagem gratuita, o servidor pode levar cerca de 1 minuto para iniciar.
          </p>
        )}
      </section>

      {items.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
          <div className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Preenchimento de Respostas</h2>
              <p className="text-sm text-slate-600">
                Escolha o modo de preenchimento de sua preferência.
              </p>
            </div>

            {/* Alternador de Modo */}
            <div className="flex rounded-lg border border-slate-300 bg-slate-100 p-1">
              <button
                type="button"
                onClick={() => setInputMode("check")}
                className={`rounded-md px-3.5 py-1.5 text-xs font-semibold transition ${
                  inputMode === "check"
                    ? "bg-white text-emerald-800 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                ✓ Modo Rápido (Apenas Acertos)
              </button>
              <button
                type="button"
                onClick={() => setInputMode("letters")}
                className={`rounded-md px-3.5 py-1.5 text-xs font-semibold transition ${
                  inputMode === "letters"
                    ? "bg-white text-blue-800 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Alternativas A–E
              </button>
            </div>
          </div>

          {inputMode === "check" ? (
            <div className="mt-6 space-y-4">
              <div className="flex flex-col gap-3 rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-600 text-xs font-bold text-white">
                      ✓
                    </span>
                    <h3 className="font-semibold text-emerald-950">
                      Modo Rápido: Marque apenas as que acertou
                    </h3>
                  </div>
                  <p className="mt-1 text-xs text-emerald-900">
                    Clique nas questões que você acertou para marcá-las com <strong>check (✓)</strong>. As que você deixar em branco serão consideradas <strong>erradas</strong> no cálculo da TRI.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={selectAll}
                    className="rounded-lg border border-emerald-300 bg-white px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-100"
                  >
                    Marcar Todas
                  </button>
                  <button
                    type="button"
                    onClick={clearAll}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  >
                    Desmarcar Todas
                  </button>
                </div>
              </div>

              {/* Barra de resumo de acertos */}
              <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3 text-sm">
                <span className="font-medium text-slate-700">
                  Acertos marcados:{" "}
                  <strong className="text-emerald-700 text-base">{correctCount}</strong> de {totalCount} questões válidas
                </span>
                <span className="text-xs font-semibold text-slate-500">
                  {totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0}% de aproveitamento
                </span>
              </div>

              {/* Grade de questões para check */}
              <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-6">
                {items.map((item) => {
                  const isChecked = checkedPositions.has(item.physical_position);
                  return (
                    <button
                      key={item.physical_position}
                      type="button"
                      disabled={item.annulled}
                      onClick={() => toggleCheck(item.physical_position)}
                      className={`flex flex-col items-center justify-center rounded-xl border p-3 transition focus:outline-none focus:ring-2 focus:ring-offset-1 ${
                        item.annulled
                          ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400 opacity-60"
                          : isChecked
                          ? "border-emerald-600 bg-emerald-600 text-white shadow-sm ring-emerald-500"
                          : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:bg-slate-100"
                      }`}
                    >
                      <span className="text-xs font-bold uppercase tracking-wider opacity-80">
                        Q{item.physical_position} · {item.area}
                      </span>
                      <span className="mt-1 flex items-center gap-1 text-sm font-semibold">
                        {item.annulled ? (
                          "Anulada"
                        ) : isChecked ? (
                          <>
                            <svg
                              className="h-4 w-4"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth={3}
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M5 13l4 4L19 7"
                              />
                            </svg>
                            Acertou
                          </>
                        ) : (
                          <span className="text-slate-400 font-normal">Em branco</span>
                        )}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="mt-6 space-y-4">
              <p className="text-sm text-slate-600">
                {Object.keys(answers).length} de {validItems.length} questões respondidas.
              </p>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {items.map((item) => (
                  <fieldset
                    key={item.physical_position}
                    disabled={item.annulled}
                    className="rounded-lg border border-slate-200 p-3 disabled:opacity-50"
                  >
                    <legend className="px-1 text-sm font-semibold text-slate-800">
                      Q{item.physical_position} · {item.area}
                      {item.annulled ? " · anulada" : ""}
                    </legend>
                    <div className="mt-1 flex gap-1">
                      {choices.map((choice) => (
                        <button
                          type="button"
                          key={choice}
                          onClick={() =>
                            setAnswers((prev) => ({
                              ...prev,
                              [item.physical_position]: choice,
                            }))
                          }
                          className={`min-h-10 min-w-10 rounded-lg text-sm font-semibold transition ${
                            answers[item.physical_position] === choice
                              ? "bg-blue-700 text-white shadow-sm"
                              : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                          }`}
                        >
                          {choice}
                        </button>
                      ))}
                    </div>
                  </fieldset>
                ))}
              </div>
            </div>
          )}

          {error && (
            <p role="alert" className="mt-6 rounded-lg bg-red-50 p-3 text-sm text-red-800">
              {error}
            </p>
          )}

          <div className="mt-8 flex items-center justify-between border-t border-slate-200 pt-5">
            <span className="text-xs text-slate-500">
              {inputMode === "check"
                ? `${correctCount} acertos marcados prontos para envio.`
                : `${Object.keys(answers).length} respostas preenchidas.`}
            </span>

            <button
              onClick={score}
              disabled={busy || !signedIn}
              className="rounded-xl bg-emerald-700 px-6 py-3.5 text-sm font-semibold text-white shadow hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:ring-offset-2 disabled:opacity-50"
            >
              {busy ? "Calculando Estimativa..." : "Calcular Nota TRI"}
            </button>
          </div>
        </section>
      )}

      {error && items.length === 0 && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      )}
    </main>
  );
}
