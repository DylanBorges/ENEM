"use client";

import { useEffect, useRef, useState } from "react";
import type { PDFDocumentProxy } from "pdfjs-dist";

type Props = { url: string; initialPage: number; questionNumber: number };

export function QuestionPaper({ url, initialPage, questionNumber }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const [document, setDocument] = useState<PDFDocumentProxy | null>(null);
  const [page, setPage] = useState(initialPage);
  const [zoom, setZoom] = useState(1);
  const [width, setWidth] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setPage(initialPage);
    setZoom(1);
  }, [url, initialPage]);

  useEffect(() => {
    const element = viewportRef.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setWidth(element.clientWidth));
    observer.observe(element);
    setWidth(element.clientWidth);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let active = true;
    let task: ReturnType<typeof import("pdfjs-dist")["getDocument"]> | null = null;
    setDocument(null);
    setLoading(true);
    setError("");
    import("pdfjs-dist").then((pdfjs) => {
      if (!active) return;
      pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
      task = pdfjs.getDocument({ url });
      return task.promise;
    }).then((pdf) => {
      if (active && pdf) setDocument(pdf);
      else pdf?.destroy();
    }).catch(() => {
      if (active) { setError("Não foi possível carregar o caderno oficial nesta página."); setLoading(false); }
    });
    return () => {
      active = false;
      if (task) void task.destroy();
    };
  }, [url]);

  useEffect(() => {
    if (!document || !width || !canvasRef.current) return;
    let active = true;
    let renderTask: ReturnType<Awaited<ReturnType<PDFDocumentProxy["getPage"]>>["render"]> | null = null;
    setLoading(true);
    setError("");
    document.getPage(page).then((pdfPage) => {
      if (!active || !canvasRef.current) return;
      const base = pdfPage.getViewport({ scale: 1 });
      const scale = ((Math.max(width - 4, 300) * zoom) / base.width);
      const viewport = pdfPage.getViewport({ scale });
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      const canvas = canvasRef.current;
      canvas.width = Math.floor(viewport.width * pixelRatio);
      canvas.height = Math.floor(viewport.height * pixelRatio);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Canvas indisponível");
      renderTask = pdfPage.render({ canvasContext: context, viewport, transform: [pixelRatio, 0, 0, pixelRatio, 0, 0] });
      return renderTask.promise;
    }).then(() => { if (active) setLoading(false); }).catch((cause) => {
      if (active && cause?.name !== "RenderingCancelledException") {
        setError("Não foi possível mostrar esta página do caderno.");
        setLoading(false);
      }
    });
    return () => { active = false; renderTask?.cancel(); };
  }, [document, page, width, zoom]);

  return <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-label="Enunciado no caderno oficial">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 sm:px-5">
      <div>
        <h2 className="font-semibold text-slate-900">Leia a questão {questionNumber}</h2>
        <p className="text-xs text-slate-600">Página {page}{document ? ` de ${document.numPages}` : ""} do caderno oficial</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={() => setPage((value) => value - 1)} disabled={page <= 1} aria-label="Página anterior" className="min-h-10 rounded-lg border border-slate-300 px-3 text-sm font-medium disabled:opacity-40">← Página</button>
        <button type="button" onClick={() => setPage((value) => value + 1)} disabled={!document || page >= document.numPages} aria-label="Próxima página" className="min-h-10 rounded-lg border border-slate-300 px-3 text-sm font-medium disabled:opacity-40">Página →</button>
        <button type="button" onClick={() => setZoom((value) => Math.max(1, value - 0.25))} disabled={zoom <= 1} aria-label="Diminuir zoom" className="min-h-10 min-w-10 rounded-lg border border-slate-300 text-lg disabled:opacity-40">−</button>
        <span className="min-w-11 text-center text-xs text-slate-600" aria-label={`Zoom ${Math.round(zoom * 100)} por cento`}>{Math.round(zoom * 100)}%</span>
        <button type="button" onClick={() => setZoom((value) => Math.min(2.5, value + 0.25))} disabled={zoom >= 2.5} aria-label="Aumentar zoom" className="min-h-10 min-w-10 rounded-lg border border-slate-300 text-lg disabled:opacity-40">+</button>
      </div>
    </div>
    <div ref={viewportRef} className="relative max-h-[75vh] min-h-80 overflow-auto bg-slate-100 p-2 text-center sm:p-4">
      {loading && <p role="status" className="absolute inset-x-4 top-5 rounded-lg bg-white/90 p-3 text-sm text-slate-700">Carregando página oficial…</p>}
      {error && <p role="alert" className="m-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error} <a className="underline" href={`${url}#page=${page}`} target="_blank" rel="noopener noreferrer">Abrir PDF oficial</a></p>}
      <canvas ref={canvasRef} aria-label={`Página ${page} do caderno oficial com a questão ${questionNumber}`} className="mx-auto bg-white shadow" />
    </div>
    <p className="border-t border-slate-200 px-4 py-2 text-xs text-slate-600 sm:px-5">A página pode conter mais de uma questão. Localize o número {questionNumber} no caderno e marque a alternativa abaixo.</p>
  </section>;
}
